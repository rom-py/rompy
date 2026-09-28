"""Focused issue #4 tests for canonical results and sidecars."""

import json
from datetime import datetime, timezone

import pytest
from pydantic import TypeAdapter, ValidationError

from rompy.core import result_persistence
from rompy.core.responses import (
    ArtifactIdentity,
    GenerateFailure,
    GenerateResult,
    LocalArtifact,
    ModelRunFailure,
    ModelRunResult,
    ModelRunSuccess,
    PersistenceDiagnostic,
    PipelineFailure,
    PipelineResult,
    PipelineStage,
    PostprocessFailure,
    PostprocessResult,
    RemoteArtifact,
    RunResultSidecar,
    TimingInfo,
)

START = datetime(2026, 3, 10, 10, 0, tzinfo=timezone.utc)


def timing(seconds=2.25):
    from datetime import timedelta

    return TimingInfo(start_time=START, end_time=START + timedelta(seconds=seconds))


def run_success():
    return ModelRunSuccess(
        run_id="run-42",
        backend_used="local",
        output_dir="results/run-42",
        timing=timing(),
        artifacts=[LocalArtifact(path="outputs/waves.nc"), RemoteArtifact(uri="s3://bucket/run-42/summary.json")],
        expected_outputs=[LocalArtifact(path="outputs/waves.nc")],
        missing_outputs=[LocalArtifact(path="outputs/wind.nc", reason="not produced")],
        metadata={"attempt": 1},
    )


def test_timing_is_numeric_and_utc():
    assert run_success().timing.duration_seconds == 2.25
    assert run_success().timing.model_dump(mode="json")["duration_seconds"] == 2.25

    with pytest.raises(ValidationError, match="UTC"):
        TimingInfo(start_time=datetime.fromisoformat("2026-01-01"), end_time=START)
    with pytest.raises(ValidationError, match="duration_seconds"):
        TimingInfo(start_time=START, end_time=START, duration_seconds="1s")
    with pytest.raises(ValidationError, match="end_time"):
        TimingInfo(start_time=START, end_time=START.replace(year=2025))


def test_artifact_union_rejects_unsafe_identities():
    adapter = TypeAdapter(ArtifactIdentity)
    with pytest.raises(ValidationError):
        adapter.validate_python({"kind": "local", "path": "../outside.nc"})
    with pytest.raises(ValidationError):
        adapter.validate_python({"kind": "local", "path": "/absolute.nc"})
    with pytest.raises(ValidationError):
        adapter.validate_python({"kind": "local", "path": "s3://bucket/x"})
    with pytest.raises(ValidationError):
        adapter.validate_python({"kind": "remote", "uri": "file:///tmp/x"})


def test_union_rejects_contradictory_result_state():
    adapter = TypeAdapter(ModelRunResult)
    raw = run_success().model_dump(mode="json")
    raw["success"] = False
    with pytest.raises(ValidationError):
        adapter.validate_python(raw)


def test_sidecar_round_trip_is_current_and_deterministic(tmp_path):
    sidecar = RunResultSidecar(run_id="run-42", status="success", success=True, payload=run_success())
    first = result_persistence.write_run_result(tmp_path, sidecar)
    first_bytes = first.read_bytes()
    result_persistence.write_run_result(tmp_path, sidecar)
    assert first_bytes == first.read_bytes()
    loaded = result_persistence.load_run_result(first)
    assert loaded.payload.model_dump(mode="json") == sidecar.payload.model_dump(mode="json")
    assert json.loads(first.read_text())["schema_version"] == 2


def test_loader_rejects_mismatch_and_legacy(tmp_path):
    sidecar = RunResultSidecar(run_id="run-42", status="success", success=True, payload=run_success())
    path = result_persistence.write_run_result(tmp_path, sidecar)
    raw = json.loads(path.read_text())
    raw["payload"]["run_id"] = "other"
    path.write_text(json.dumps(raw))
    with pytest.raises(ValueError, match="run_id"):
        result_persistence.load_run_result(path)

    raw["schema_version"] = 1
    path.write_text(json.dumps(raw))
    with pytest.raises(ValueError, match="schema_version"):
        result_persistence.load_run_result(path)


def test_replace_failure_cleans_temp_and_preserves_previous(tmp_path, monkeypatch):
    sidecar = RunResultSidecar(run_id="run-42", status="success", success=True, payload=run_success())
    path = result_persistence.write_run_result(tmp_path, sidecar)
    previous = path.read_bytes()

    def fail_replace(source, destination):
        raise OSError("interrupted replace")

    monkeypatch.setattr(result_persistence.os, "replace", fail_replace)
    with pytest.raises(OSError, match="interrupted replace"):
        result_persistence.write_run_result(tmp_path, sidecar)
    assert path.read_bytes() == previous
    assert list(tmp_path.glob(".*run_result.json.*")) == []


def test_failure_variants_require_non_empty_errors():
    generate = GenerateFailure(
        run_id="run-42",
        error="generation failed",
        generated_files=[],
        timing=timing(),
    )
    run = ModelRunFailure(
        run_id="run-42",
        backend_used="local",
        error="run failed",
        timing=timing(),
        artifacts=[],
        expected_outputs=[],
        missing_outputs=[],
    )
    postprocess = PostprocessFailure(
        run_id="run-42",
        error="postprocess failed",
        timing=timing(),
        artifacts=[],
        expected_outputs=[],
        missing_outputs=[],
    )
    pipeline = PipelineFailure(
        run_id="run-42",
        stages_completed=[],
        backend="local",
        processor="noop",
        failed_stage=PipelineStage.GENERATE,
        error="pipeline failed",
        timing=timing(),
        cleaned_up=False,
        generate_result=generate,
    )
    variants = [
        (GenerateFailure, GenerateResult, generate),
        (ModelRunFailure, ModelRunResult, run),
        (PostprocessFailure, PostprocessResult, postprocess),
        (PipelineFailure, PipelineResult, pipeline),
    ]
    for model, union, result in variants:
        for invalid in ("", "   ", None):
            raw = result.model_dump(mode="json")
            raw["error"] = invalid
            with pytest.raises(ValidationError):
                model.model_validate(raw)
            with pytest.raises(ValidationError):
                TypeAdapter(union).validate_python(raw)

    nested = pipeline.model_dump(mode="json")
    nested["generate_result"]["error"] = ""
    with pytest.raises(ValidationError):
        TypeAdapter(PipelineResult).validate_python(nested)

    sidecar = RunResultSidecar(
        run_id="run-42", status="success", success=True, payload=run_success()
    ).model_dump(mode="json")
    sidecar["error"] = " "
    with pytest.raises(ValidationError):
        RunResultSidecar.model_validate(sidecar)


def test_persistence_diagnostic_preserves_primary_error():
    result = ModelRunFailure(
        run_id="run-42",
        backend_used="local",
        error="model failed",
        timing=timing(),
        artifacts=[],
        expected_outputs=[],
        missing_outputs=[],
        persistence_diagnostic=PersistenceDiagnostic(
            sidecar_kind="run_result",
            sidecar_path="/tmp/run_result.json",
            error="permission denied",
            primary_error="model failed",
        ),
    )
    rebuilt = ModelRunFailure.model_validate(result.model_dump(mode="json"))
    assert rebuilt.persistence_diagnostic.primary_error == "model failed"