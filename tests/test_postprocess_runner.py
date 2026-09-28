"""Focused coverage for ordered composition and generic transfer."""
import json
from datetime import datetime, timezone

import pytest

from rompy.core.responses import (
    ArtifactType,
    LocalArtifact,
    ModelRunFailure,
    ModelRunSuccess,
    PostprocessFailure,
    PostprocessSuccess,
    TimingInfo,
)
from rompy.model import ModelRun
from rompy.postprocess import PostprocessContext, PostprocessFailurePolicy
from rompy.postprocess.runner import run_postprocess_pipeline
from rompy.postprocess.transfer import (
    TransferPostprocessor,
    TransferPostprocessorConfig,
)

NOW = datetime.now(timezone.utc)


def _run(tmp_path):
    output = tmp_path / "output"
    output.mkdir()
    (output / "result.txt").write_text("result")
    artifact = LocalArtifact(path="result.txt", artifact_type=ArtifactType.TEXT)
    return ModelRunSuccess(
        run_id="runner-test",
        backend_used="test",
        output_dir=str(output),
        workspace_dir=str(tmp_path),
        artifacts=[artifact],
        expected_outputs=[artifact],
        missing_outputs=[],
        timing=TimingInfo(start_time=NOW, end_time=NOW),
    )


class _Step:
    input_protocol = "context"

    def __init__(self, name, fail=False):
        self.name = name
        self.fail = fail

    def process(self, context):
        if self.fail:
            return PostprocessFailure(
                run_id=context.run_result.run_id,
                error=f"{self.name} failed",
                output_dir=str(context.output_dir),
                artifacts=list(context.artifacts),
                expected_outputs=list(context.expected_outputs),
                missing_outputs=list(context.missing_outputs),
                timing=TimingInfo(start_time=NOW, end_time=NOW),
            )
        return PostprocessSuccess(
            run_id=context.run_result.run_id,
            output_dir=str(context.output_dir),
            validated=True,
            artifacts=list(context.artifacts),
            expected_outputs=list(context.expected_outputs),
            missing_outputs=list(context.missing_outputs),
            timing=TimingInfo(start_time=NOW, end_time=NOW),
        )


def _failed_run(tmp_path):
    return ModelRunFailure(
        run_id="runner-test",
        backend_used="test",
        error="model run failed",
        output_dir=str(tmp_path),
        workspace_dir=str(tmp_path),
        artifacts=[],
        expected_outputs=[],
        missing_outputs=[],
        timing=TimingInfo(start_time=NOW, end_time=NOW),
    )


def test_no_source_transfer_stays_successful_for_successful_run(tmp_path):
    result = run_postprocess_pipeline(
        _run(tmp_path),
        [
            TransferPostprocessor(
                TransferPostprocessorConfig(
                    destinations=["file:///archive"],
                    artifact_types=[ArtifactType.NETCDF],
                )
            )
        ],
        staging_dir=tmp_path,
    )

    assert isinstance(result, PostprocessSuccess)
    assert result.file_count == 0
    assert result.metadata["postprocess_pipeline"]["steps"] == [
        {"name": "transfer", "status": "succeeded"}
    ]


def test_failed_model_run_stays_primary_when_no_source_transfer_succeeds(tmp_path):
    result = run_postprocess_pipeline(
        _failed_run(tmp_path),
        [
            TransferPostprocessor(
                TransferPostprocessorConfig(
                    destinations=["file:///archive"],
                    artifact_types=[ArtifactType.NETCDF],
                )
            )
        ],
        staging_dir=tmp_path,
    )

    assert isinstance(result, PostprocessFailure)
    assert result.error == "model run failed"
    evidence = result.metadata["postprocess_pipeline"]
    assert evidence["primary_error"] == "model run failed"
    assert evidence["initial_run_failure"]["backend_used"] == "test"
    assert evidence["steps"] == [{"name": "transfer", "status": "succeeded"}]
    sidecar = json.loads((tmp_path / "postprocess_result.json").read_text())
    assert sidecar["success"] is False
    assert sidecar["error"] == "model run failed"


def test_fail_fast_retains_unattempted_and_one_sidecar(tmp_path):
    result = run_postprocess_pipeline(
        _run(tmp_path), [_Step("first", True), _Step("second")], staging_dir=tmp_path
    )
    assert not result.success
    assert [item["status"] for item in result.metadata["postprocess_pipeline"]["steps"]] == [
        "failed",
        "unattempted",
    ]
    assert (tmp_path / "postprocess_result.json").exists()


def test_continue_retains_primary_and_secondary_errors(tmp_path):
    result = run_postprocess_pipeline(
        _run(tmp_path),
        [_Step("first", True), _Step("second", True)],
        staging_dir=tmp_path,
        failure_policy=PostprocessFailurePolicy.CONTINUE,
    )
    assert not result.success
    evidence = result.metadata["postprocess_pipeline"]
    assert evidence["primary_error"] == "first failed"
    assert evidence["secondary_errors"] == ["second failed"]


def test_transfer_redacts_credentials_and_reuses_success(monkeypatch, tmp_path):
    import rompy.postprocess.transfer as transfer_module

    calls = []

    class Destination:
        def put(self, source, destination):
            calls.append((source, destination))

    monkeypatch.setattr(transfer_module, "get_transfer", lambda _: Destination())
    context = PostprocessContext.from_run_result(_run(tmp_path), staging_dir=tmp_path)
    processor = TransferPostprocessor(
        TransferPostprocessorConfig(
            destinations=["file://user:secret@example.test/archive"],
            artifact_types=[ArtifactType.TEXT],
        )
    )
    first = processor.process(context)
    assert first.success
    assert "secret" not in first.model_dump_json()
    context = context.with_state("transfer", processor._state_updates)
    second = processor.process(context)
    assert second.success
    assert len(calls) == 1
    assert all("secret" not in str(item) for item in calls)


def test_signed_url_is_live_only_and_fragments_are_not_evidence(monkeypatch, tmp_path):
    import rompy.postprocess.transfer as transfer_module

    calls = []
    destination = "https://user:password@example.test/archive?token=secret-token&X-Amz-Signature=sig#fragment"

    class Destination:
        def put(self, source, target):
            calls.append(target)

    monkeypatch.setattr(transfer_module, "get_transfer", lambda value: Destination())
    result = TransferPostprocessor(
        TransferPostprocessorConfig(destinations=[destination], artifact_types=[ArtifactType.TEXT])
    ).process(PostprocessContext.from_run_result(_run(tmp_path), staging_dir=tmp_path))

    assert result.success
    assert "secret-token" in calls[0]
    evidence = result.model_dump_json()
    assert all(secret not in evidence for secret in ("password", "secret-token", "X-Amz-Signature", "fragment"))
    state = next((tmp_path / ".rompy-postprocess").rglob("transfer-state.json")).read_text()
    assert all(secret not in state for secret in ("password", "secret-token", "X-Amz-Signature", "fragment"))


def test_transfer_failure_redacts_decoded_query_and_fragment(monkeypatch, tmp_path):
    import rompy.postprocess.transfer as transfer_module

    destination = (
        "https://user:password@example.test/archive?token=s%65cret"
        "&signature=abc%2Fdef#frag%6Dent"
    )
    calls = []

    class Destination:
        def put(self, source, target):
            calls.append(target)
            raise RuntimeError(
                "backend rejected token=secret signature=abc/def fragment=fragment"
            )

    monkeypatch.setattr(transfer_module, "get_transfer", lambda value: Destination())
    processor = TransferPostprocessor(
        TransferPostprocessorConfig(
            destinations=[destination], artifact_types=[ArtifactType.TEXT]
        )
    )
    result = run_postprocess_pipeline(
        _run(tmp_path), [processor], staging_dir=tmp_path
    )

    assert not result.success
    assert calls and "token=s%65cret" in calls[0]
    evidence = result.model_dump_json()
    assert all(
        value not in evidence
        for value in (
            "s%65cret",
            "secret",
            "frag%6Dent",
            "fragment",
            "abc%2Fdef",
            "abc/def",
        )
    )
    persisted = (tmp_path / "postprocess_result.json").read_text()
    assert all(
        value not in persisted
        for value in (
            "s%65cret",
            "secret",
            "frag%6Dent",
            "fragment",
            "abc%2Fdef",
            "abc/def",
        )
    )


def test_successful_pairs_replay_from_disk_after_partial_failure(monkeypatch, tmp_path):
    import rompy.postprocess.transfer as transfer_module

    calls = []
    failed_once = {"value": True}
    destinations = ["s3://bucket/first?token=one", "s3://bucket/second?token=two"]

    class Destination:
        def __init__(self, target):
            self.target = target

        def put(self, source, target):
            calls.append(target)
            if "second" in target and failed_once["value"]:
                raise RuntimeError(f"upload failed for {target}")

    monkeypatch.setattr(transfer_module, "get_transfer", lambda value: Destination(value))
    config = TransferPostprocessorConfig(
        destinations=destinations,
        artifact_types=[ArtifactType.TEXT],
        failure_policy=PostprocessFailurePolicy.CONTINUE,
    )
    context = PostprocessContext.from_run_result(_run(tmp_path), staging_dir=tmp_path)
    first = TransferPostprocessor(config).process(context)
    assert not first.success
    failed_once["value"] = False
    second = TransferPostprocessor(config).process(context)

    assert second.success
    assert len(calls) == 3
    assert sum("first" in target for target in calls) == 1
    assert second.metadata["transfer"]["replayed_pairs"] == 1
    assert "token=one" not in json.dumps(second.model_dump(mode="json"))


def test_state_namespace_rejects_traversal_and_absolute_values():
    for namespace in ("../escape", "/absolute", "nested/name", ".", ".."):
        with pytest.raises(ValueError, match="state_namespace"):
            TransferPostprocessorConfig(destinations=["file:///tmp"], state_namespace=namespace)


def test_unmarked_named_legacy_plugin_uses_result_protocol(tmp_path):
    class NamedLegacy:
        name = "named-legacy"

        def process(self, result):
            assert isinstance(result, ModelRunSuccess)
            return PostprocessSuccess(
                run_id=result.run_id,
                output_dir=result.output_dir,
                validated=True,
                artifacts=list(result.artifacts),
                expected_outputs=list(result.expected_outputs),
                missing_outputs=list(result.missing_outputs),
                timing=TimingInfo(start_time=NOW, end_time=NOW),
            )

    result = run_postprocess_pipeline(_run(tmp_path), [NamedLegacy()], staging_dir=tmp_path)
    assert result.success


def test_standalone_transfer_uses_legacy_adapter(monkeypatch, tmp_path):
    import rompy.postprocess.transfer as transfer_module

    calls = []

    class Destination:
        def put(self, source, target):
            calls.append(target)

    monkeypatch.setattr(transfer_module, "get_transfer", lambda _: Destination())
    run_result = _run(tmp_path)
    model = ModelRun(run_id=run_result.run_id, output_dir=tmp_path)
    model.staging_dir.mkdir(parents=True, exist_ok=True)
    result = model.postprocess(
        TransferPostprocessorConfig(destinations=["file:///archive"], artifact_types=[ArtifactType.TEXT]),
        processor_input=run_result,
    )
    assert result.success
    assert calls == ["file:///archive/result.txt"]
