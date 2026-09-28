"""Unit tests for the canonical issue #4 response schemas."""

import json
from datetime import datetime, timedelta, timezone

import pytest
from pydantic import TypeAdapter, ValidationError

from rompy.core.responses import (
    ArtifactIdentity,
    ArtifactType,
    GenerateFailure,
    GenerateResult,
    GenerateResultSidecar,
    GenerateSuccess,
    LocalArtifact,
    ModelRunFailure,
    ModelRunResult,
    ModelRunSuccess,
    PersistenceDiagnostic,
    PipelineFailure,
    PipelineResult,
    PipelineStage,
    PipelineSuccess,
    PostprocessFailure,
    PostprocessResultSidecar,
    PostprocessSuccess,
    RemoteArtifact,
    RunResultSidecar,
    StageTiming,
    TimingInfo,
)

START = datetime(2026, 3, 10, 10, 0, tzinfo=timezone.utc)


def timing(seconds: float = 1.0) -> TimingInfo:
    return TimingInfo(start_time=START, end_time=START + timedelta(seconds=seconds))


def post_success(run_id: str = "run-1") -> PostprocessSuccess:
    return PostprocessSuccess(
        run_id=run_id,
        output_dir="results/run-1",
        validated=True,
        timing=timing(2.0),
        artifacts=[LocalArtifact(path="outputs/waves.nc", artifact_type=ArtifactType.NETCDF)],
        expected_outputs=[LocalArtifact(path="outputs/waves.nc")],
        missing_outputs=[LocalArtifact(path="outputs/wind.nc", reason="not produced")],
    )


def run_success(run_id: str = "run-1") -> ModelRunSuccess:
    return ModelRunSuccess(
        run_id=run_id,
        backend_used="local",
        output_dir="results/run-1",
        timing=timing(2.25),
        artifacts=[
            LocalArtifact(path="outputs/waves.nc", artifact_type=ArtifactType.NETCDF),
            RemoteArtifact(uri="s3://bucket/run-1/summary.json"),
        ],
        expected_outputs=[LocalArtifact(path="outputs/waves.nc")],
        missing_outputs=[LocalArtifact(path="outputs/wind.nc", reason="not produced")],
    )


class TestArtifactIdentity:
    def test_local_and_remote_variants_round_trip(self):
        adapter = TypeAdapter(ArtifactIdentity)
        local = adapter.validate_python({"kind": "local", "path": "outputs/waves.nc"})
        remote = adapter.validate_python({"kind": "remote", "uri": "s3://bucket/summary.json"})
        assert local.path == "outputs/waves.nc"
        assert remote.uri == "s3://bucket/summary.json"

    @pytest.mark.parametrize(
        "raw",
        [
            {"kind": "local", "path": "../outside.nc"},
            {"kind": "local", "path": "/absolute.nc"},
            {"kind": "local", "path": "s3://bucket/output.nc"},
            {"kind": "remote", "uri": "file:///tmp/output.nc"},
        ],
    )
    def test_rejects_unsafe_or_ambiguous_identity(self, raw):
        with pytest.raises(ValidationError):
            TypeAdapter(ArtifactIdentity).validate_python(raw)

    def test_artifact_metadata_is_preserved(self):
        artifact = LocalArtifact(
            path="outputs/waves.nc",
            artifact_type=ArtifactType.NETCDF,
            size_bytes=2048,
            description="wave output",
        )
        restored = LocalArtifact.model_validate(artifact.model_dump(mode="json"))
        assert restored == artifact


class TestTimingInfo:
    def test_duration_is_computed_as_numeric_seconds(self):
        value = timing(2.25)
        assert value.duration_seconds == 2.25
        assert value.model_dump(mode="json")["duration_seconds"] == 2.25

    def test_rejects_nonfinite_and_naive_non_utc_reversed_and_mismatched_timing(self):
        for value in (float("nan"), float("inf"), float("-inf")):
            with pytest.raises(ValidationError, match="finite"):
                TimingInfo(start_time=START, end_time=START, duration_seconds=value)
        with pytest.raises(ValidationError, match="UTC"):
            TimingInfo(start_time=datetime.fromisoformat("2026-01-01"), end_time=START)
        with pytest.raises(ValidationError, match="UTC"):
            TimingInfo(
                start_time=START.replace(tzinfo=timezone(timedelta(hours=1))),
                end_time=START,
            )
        with pytest.raises(ValidationError, match="end_time"):
            TimingInfo(start_time=START, end_time=START - timedelta(seconds=1))
        with pytest.raises(ValidationError, match="duration_seconds"):
            TimingInfo(start_time=START, end_time=START, duration_seconds="1s")
        with pytest.raises(ValidationError, match="does not match"):
            TimingInfo(start_time=START, end_time=START, duration_seconds=1)


class TestTypedResults:
    def test_postprocess_success_and_failure_are_typed(self):
        success = post_success()
        failure = PostprocessFailure(
            run_id="run-1",
            error="validation failed",
            output_dir="results/run-1",
            timing=timing(),
            artifacts=success.artifacts,
            expected_outputs=success.expected_outputs,
            missing_outputs=success.missing_outputs,
        )
        assert success.success is True
        assert failure.success is False
        assert failure.error == "validation failed"

    def test_model_run_union_deserializes_concrete_variant(self):
        raw = run_success().model_dump(mode="json")
        restored = TypeAdapter(ModelRunResult).validate_python(raw)
        assert isinstance(restored, ModelRunSuccess)
        assert restored.artifacts[1].uri == "s3://bucket/run-1/summary.json"
        assert restored.missing_outputs[0].reason == "not produced"

    def test_required_evidence_fields_must_be_present_on_load(self):
        raw = run_success().model_dump(mode="json")
        for field in ("artifacts", "expected_outputs", "missing_outputs"):
            missing = dict(raw)
            missing.pop(field)
            with pytest.raises(ValidationError, match=field):
                TypeAdapter(ModelRunResult).validate_python(missing)

        pipeline = PipelineSuccess(
            run_id="run-1",
            stages_completed=list(PipelineStage),
            backend="local",
            processor="processor",
            staging_dir="staging/run-1",
            output_dir="results/run-1",
            postprocess_results=post_success(),
            timing=timing(5),
            stage_timings=[
                StageTiming(stage=stage, timing=timing(1)) for stage in PipelineStage
            ],
        ).model_dump(mode="json")
        pipeline.pop("stage_timings")
        with pytest.raises(ValidationError, match="stage_timings"):
            TypeAdapter(PipelineResult).validate_python(pipeline)

    def test_generate_union_requires_variant_fields(self):
        success = GenerateSuccess(
            run_id="run-1",
            staging_dir="staging/run-1",
            generated_files=["config.nml"],
            timing=timing(),
        )
        failure = GenerateFailure(
            run_id="run-1",
            error="render failed",
            generated_files=[],
            timing=timing(),
        )
        assert isinstance(TypeAdapter(GenerateResult).validate_python(success.model_dump()), GenerateSuccess)
        assert isinstance(TypeAdapter(GenerateResult).validate_python(failure.model_dump()), GenerateFailure)
        with pytest.raises(ValidationError):
            TypeAdapter(GenerateResult).validate_python({"success": True, "run_id": "run-1"})
        with pytest.raises(ValidationError):
            GenerateSuccess(
                run_id="run-1",
                staging_dir="staging/run-1",
                generated_files=[],
                timing=timing(),
                generated_at=START,
            )

    def test_persistence_diagnostic_round_trip_preserves_primary_error(self):
        result = ModelRunFailure(
            run_id="run-1",
            backend_used="local",
            error="model failed",
            timing=timing(),
            artifacts=[],
            expected_outputs=[],
            missing_outputs=[],
            persistence_diagnostic=PersistenceDiagnostic(
                sidecar_kind="run_result",
                sidecar_path="staging/run-1/run_result.json",
                error="permission denied",
                primary_error="model failed",
            ),
        )
        restored = ModelRunFailure.model_validate(result.model_dump(mode="json"))
        assert restored.persistence_diagnostic.primary_error == "model failed"

    def test_metadata_must_be_json_safe(self):
        with pytest.raises(ValidationError, match="JSON-safe"):
            ModelRunSuccess(
                run_id="run-1",
                backend_used="local",
                output_dir="results/run-1",
                timing=timing(),
                artifacts=[],
                expected_outputs=[],
                missing_outputs=[],
                metadata={"bad": object()},
            )


class TestPipelineResult:
    def test_success_requires_exact_stage_sequence_and_nested_success(self):
        result = PipelineSuccess(
            run_id="run-1",
            stages_completed=list(PipelineStage),
            backend="local",
            processor="processor",
            staging_dir="staging/run-1",
            output_dir="results/run-1",
            postprocess_results=post_success(),
            timing=timing(5),
            stage_timings=[
                StageTiming(stage=stage, timing=timing(1)) for stage in PipelineStage
            ],
        )
        restored = TypeAdapter(PipelineResult).validate_python(result.model_dump(mode="json"))
        assert isinstance(restored, PipelineSuccess)
        assert restored.stages_completed == list(PipelineStage)

    @pytest.mark.parametrize(
        ("failed_stage", "stages_completed"),
        [
            (PipelineStage.GENERATE, []),
            (PipelineStage.RUN, [PipelineStage.GENERATE]),
            (PipelineStage.POSTPROCESS, [PipelineStage.GENERATE, PipelineStage.RUN]),
        ],
    )
    def test_failure_requires_strict_successful_prefix(self, failed_stage, stages_completed):
        kwargs = {
            "run_id": "run-1",
            "stages_completed": stages_completed,
            "backend": "local",
            "processor": "processor",
            "failed_stage": failed_stage,
            "error": "stage failed",
            "timing": timing(),
            "stage_timings": [],
            "cleaned_up": False,
        }
        if failed_stage is PipelineStage.POSTPROCESS:
            kwargs["postprocess_results"] = PostprocessFailure(
                run_id="run-1",
                error="postprocess failed",
                timing=timing(),
                artifacts=[],
                expected_outputs=[],
                missing_outputs=[],
            )
        result = PipelineFailure(**kwargs)
        assert failed_stage not in result.stages_completed

    def test_pipeline_rejects_bad_prefix(self):
        with pytest.raises(ValidationError, match="successful prefix"):
            PipelineFailure(
                run_id="run-1",
                stages_completed=[PipelineStage.RUN],
                backend="local",
                processor="processor",
                failed_stage=PipelineStage.RUN,
                error="failed",
                timing=timing(),
                stage_timings=[],
                cleaned_up=False,
            )


class TestEnvelopeCoherence:
    def test_matching_envelopes_round_trip(self):
        payload = run_success()
        envelope = RunResultSidecar(
            run_id="run-1", status="success", success=True, payload=payload
        )
        restored = RunResultSidecar.model_validate_json(envelope.model_dump_json())
        assert restored.schema_version == 2
        assert restored.payload.run_id == restored.run_id
        assert restored.payload.timing.duration_seconds == 2.25

    def test_mismatched_run_id_success_status_and_payload_family_rejected(self):
        raw = RunResultSidecar(
            run_id="run-1", status="success", success=True, payload=run_success()
        ).model_dump(mode="json")
        raw["run_id"] = "run-other"
        with pytest.raises(ValidationError, match="run_id"):
            RunResultSidecar.model_validate(raw)

        raw = RunResultSidecar(
            run_id="run-1", status="success", success=True, payload=run_success()
        ).model_dump(mode="json")
        raw["payload"]["success"] = False
        raw["payload"]["error"] = "failed"
        with pytest.raises(ValidationError, match="success"):
            RunResultSidecar.model_validate(raw)

        with pytest.raises(ValidationError):
            PostprocessResultSidecar(
                run_id="run-1", status="success", success=True, payload=run_success()
            )

    def test_generate_failure_envelope_requires_matching_error(self):
        payload = GenerateFailure(
            run_id="run-1", error="render failed", generated_files=[], timing=timing()
        )
        with pytest.raises(ValidationError, match="must match"):
            GenerateResultSidecar(
                run_id="run-1",
                status="failed",
                success=False,
                error="different error",
                payload=payload,
            )

    def test_sidecar_version_and_kind_are_current(self):
        payload = post_success()
        sidecar = PostprocessResultSidecar(
            run_id="run-1", status="success", success=True, payload=payload
        )
        data = json.loads(sidecar.model_dump_json())
        assert data["kind"] == "postprocess_result"
        assert data["schema_version"] == 2