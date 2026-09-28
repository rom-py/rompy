"""Contract tests for the typed postprocessor context and step protocol."""

from datetime import datetime, timezone
import math

import pytest

from rompy.core.responses import (
    ArtifactType,
    LocalArtifact,
    ModelRunSuccess,
    PostprocessSuccess,
    TimingInfo,
)
from rompy.postprocess import (
    PostprocessContext,
    PostprocessFailurePolicy,
    PostprocessProcessor,
    PostprocessStep,
)
from rompy.postprocess import NoopPostprocessor, NoopPostprocessorConfig


class EvidenceStep:
    """Minimal in-tree step used to exercise the public protocol."""

    name = "evidence"

    def process(self, context: PostprocessContext) -> PostprocessSuccess:
        return PostprocessSuccess(
            run_id=context.run_result.run_id,
            output_dir=str(context.output_dir or "outputs"),
            validated=True,
            artifacts=list(context.artifacts),
            expected_outputs=list(context.expected_outputs),
            missing_outputs=list(context.missing_outputs),
            timing=TimingInfo(start_time=NOW, end_time=NOW),
        )


NOW = datetime.now(timezone.utc)


def run_result(tmp_path):
    artifact = LocalArtifact(path="waves.nc", artifact_type=ArtifactType.NETCDF)
    return ModelRunSuccess(
        run_id="protocol-run",
        backend_used="local",
        output_dir=str(tmp_path),
        artifacts=[artifact],
        expected_outputs=[artifact],
        missing_outputs=[],
        timing=TimingInfo(start_time=NOW, end_time=NOW),
    )


def test_context_and_step_use_concrete_typed_handoff(tmp_path):
    context = PostprocessContext.from_run_result(
        run_result(tmp_path),
        staging_dir=tmp_path / "staging",
        failure_policy=PostprocessFailurePolicy.CONTINUE,
        operational_state={"example": {"attempt": 1}},
    )

    step = EvidenceStep()
    assert isinstance(step, PostprocessStep)
    assert context.namespace("example")["attempt"] == 1
    result = step.process(context)
    next_context = context.handoff(result)

    assert isinstance(result, PostprocessSuccess)
    assert next_context.artifacts == tuple(result.artifacts)
    assert next_context.failure_policy is PostprocessFailurePolicy.CONTINUE
    reconciled = context.reconcile_artifacts(artifact_types=[ArtifactType.NETCDF])
    assert reconciled.selected == [context.artifacts[0]]
    assert reconciled.missing == []


def test_operational_state_snapshots_input_and_nested_values(tmp_path):
    nested = {"attempt": 1, "items": [{"ready": True}]}
    state = {"example": nested}
    context = PostprocessContext.from_run_result(run_result(tmp_path), operational_state=state)

    nested["items"][0]["ready"] = False
    nested["items"].append({"late": True})
    state["example"] = {"replaced": True}

    assert context.namespace("example") == {
        "attempt": 1,
        "items": [{"ready": True}],
    }
    with pytest.raises(TypeError, match="immutable"):
        context.namespace("example")["items"].append({"late": True})


def test_operational_state_rejects_invalid_json_values_and_keys(tmp_path):
    for value in (math.nan, math.inf, -math.inf, object(), {1: "not a string key"}):
        with pytest.raises(ValueError, match="operational_state"):
            PostprocessContext.from_run_result(
                run_result(tmp_path), operational_state={"example": {"value": value}}
            )

    with pytest.raises(ValueError, match="namespace"):
        PostprocessContext.from_run_result(
            run_result(tmp_path), operational_state={"example": ["not a mapping"]}
        )


def test_state_update_and_handoff_are_immutable_and_isolated(tmp_path):
    context = PostprocessContext.from_run_result(
        run_result(tmp_path), operational_state={"example": {"attempt": 1}}
    )
    update = {"attempt": 2, "nested": {"ok": True}}
    updated = context.with_state("example", update)
    update["nested"]["ok"] = False

    assert context.namespace("example") == {"attempt": 1}
    assert updated.namespace("example") == {
        "attempt": 2,
        "nested": {"ok": True},
    }
    next_context = updated.handoff(
        PostprocessSuccess(
            run_id="protocol-run",
            output_dir=str(tmp_path),
            validated=True,
            artifacts=[],
            expected_outputs=[],
            missing_outputs=[],
            timing=TimingInfo(start_time=NOW, end_time=NOW),
        )
    )
    assert next_context.namespace("example") == updated.namespace("example")
    assert next_context.namespace("example") is not updated.namespace("example")


def test_existing_single_processor_conforms_without_composition(tmp_path):
    processor = NoopPostprocessor(NoopPostprocessorConfig(validate_outputs=False))
    assert isinstance(processor, PostprocessProcessor)
    result = processor.process(run_result(tmp_path))
    assert result.success is True
