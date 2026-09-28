"""Focused issue #5 runtime handoff tests."""

import time
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
from pydantic import TypeAdapter

from rompy.backends.config import LocalConfig
from rompy.cli import _build_postprocess_processor_input, _result_envelope
from rompy.core.responses import (
    GenerateFailure,
    GenerateSuccess,
    LocalArtifact,
    ModelRunFailure,
    ModelRunResult,
    ModelRunSuccess,
    PersistenceDiagnostic,
    PipelineFailure,
    PipelineStage,
    PostprocessFailure,
    PostprocessSuccess,
    TimingInfo,
)
from rompy.core.result_persistence import load_run_result
from rompy.model import ModelRun
from rompy.pipeline import LocalPipelineBackend
from rompy.postprocess import NoopPostprocessor
from rompy.postprocess.config import BasePostprocessorConfig, NoopPostprocessorConfig


def timing():
    now = datetime.now(timezone.utc)
    return TimingInfo(start_time=now, end_time=now)


class EmptyExceptionPath:
    def __fspath__(self):
        raise Exception()


def run_success(tmp_path):
    return ModelRunSuccess(
        run_id="run-5",
        backend_used="local",
        output_dir=str(tmp_path),
        timing=timing(),
        artifacts=[LocalArtifact(path="outputs/waves.nc")],
        expected_outputs=[LocalArtifact(path="outputs/waves.nc")],
        missing_outputs=[],
    )


class RecordingProcessor:
    received = None

    def __init__(self, config):
        self.config = config

    def process(self, result, **options):
        self.received = result
        type(self).received = result
        return PostprocessSuccess(
            run_id=result.run_id,
            output_dir=result.output_dir,
            validated=True,
            timing=timing(),
            artifacts=result.artifacts,
            expected_outputs=result.expected_outputs,
            missing_outputs=result.missing_outputs,
        )


class RecordingConfig(BasePostprocessorConfig):
    type: str = "recording"

    def get_postprocessor_class(self):
        return RecordingProcessor


def test_processor_constructor_and_exact_typed_input(tmp_path):
    model = ModelRun(run_id="run-5", output_dir=tmp_path)
    source = run_success(tmp_path)
    result = model.postprocess(RecordingConfig(), processor_input=source)
    assert isinstance(result, PostprocessSuccess)
    assert RecordingProcessor.received == source
    assert isinstance(RecordingProcessor.received, (ModelRunSuccess, ModelRunFailure))


@pytest.mark.parametrize("bad_input", [SimpleNamespace(run_id="run-5"), object()])
def test_processor_rejects_non_model_result_before_persistence(tmp_path, bad_input):
    model = ModelRun(run_id="run-5", output_dir=tmp_path)
    result = model.postprocess(RecordingConfig(), processor_input=bad_input)
    assert isinstance(result, PostprocessFailure)
    assert "processor protocol failure" in result.error.lower()
    assert not (model.staging_dir / "postprocess_result.json").exists()


def test_processor_rejects_arbitrary_return_before_persistence(tmp_path):
    class BadProcessor(RecordingProcessor):
        def process(self, result, **options):
            return SimpleNamespace(success=True, run_id=result.run_id)

    class BadConfig(RecordingConfig):
        def get_postprocessor_class(self):
            return BadProcessor

    model = ModelRun(run_id="run-5", output_dir=tmp_path)
    result = model.postprocess(BadConfig(), processor_input=run_success(tmp_path))
    assert isinstance(result, PostprocessFailure)
    assert "processor protocol failure" in result.error.lower()
    assert not (model.staging_dir / "postprocess_result.json").exists()


def test_output_validation_errors_are_not_converted_to_empty_success(tmp_path):
    model = ModelRun(run_id="run-5", output_dir=tmp_path)
    # Patch the class method to exercise producer validation propagation.
    with patch.object(model.config.__class__, "validate_outputs", side_effect=RuntimeError("validation failed")):
        result = model.run(LocalConfig(command="true", timeout=60), workspace_dir=str(tmp_path))
    assert isinstance(result, ModelRunFailure)
    assert "validation failed" in result.error


def test_generate_failure_preserves_path_timing_and_primary_error(tmp_path):
    model = ModelRun(run_id="run-5", output_dir=tmp_path)
    with patch.object(model.config.__class__, "render", side_effect=RuntimeError("render failed")):
        result = model.generate()
    assert isinstance(result, GenerateFailure)
    assert result.error == "render failed"
    assert result.staging_dir == str(model.staging_dir)
    assert result.timing.start_time.tzinfo is not None
    assert result.timing.end_time >= result.timing.start_time


def test_empty_generation_exception_returns_typed_failure(tmp_path):
    model = ModelRun(run_id="run-5", output_dir=tmp_path)
    with patch.object(model.config.__class__, "render", side_effect=Exception()):
        result = model.generate()
    assert isinstance(result, GenerateFailure)
    assert result.error == "model generation failed"


def test_empty_noop_postprocess_exception_returns_typed_failure(tmp_path):
    processor = NoopPostprocessor(NoopPostprocessorConfig(validate_outputs=True))
    result = processor.process(run_success(tmp_path), output_dir=EmptyExceptionPath())
    assert isinstance(result, PostprocessFailure)
    assert result.error == "postprocessing failed"


def test_empty_pipeline_stage_exception_returns_typed_failure(tmp_path):
    generated = GenerateSuccess(run_id="run-5", staging_dir=str(tmp_path), generated_files=[], timing=timing())
    model = Mock(run_id="run-5", output_dir=tmp_path, staging_dir=tmp_path)
    model.generate.return_value = generated
    model.run.return_value = run_success(tmp_path)
    model.postprocess.side_effect = Exception()
    result = LocalPipelineBackend().execute(
        model, backend_config=LocalConfig(command="true"), processor=RecordingConfig()
    )
    assert isinstance(result, PipelineFailure)
    assert result.error == "postprocessing failed"
    assert isinstance(result.postprocess_results, PostprocessFailure)
    assert result.postprocess_results.error == "postprocessing failed"


def test_empty_pipeline_outer_exception_returns_typed_failure(tmp_path):
    generated = GenerateSuccess(run_id="run-5", staging_dir=str(tmp_path), generated_files=[], timing=timing())
    model = Mock(run_id="run-5", output_dir=tmp_path, staging_dir=tmp_path)
    model.generate.return_value = generated
    model.run.return_value = SimpleNamespace(
        success=True,
        output_dir=EmptyExceptionPath(),
        workspace_dir=str(tmp_path),
        timing=timing(),
    )
    model.postprocess.return_value = PostprocessSuccess(
        run_id="run-5", output_dir=str(tmp_path), validated=True, timing=timing(),
        artifacts=[], expected_outputs=[], missing_outputs=[],
    )
    result = LocalPipelineBackend().execute(
        model, backend_config=LocalConfig(command="true"), processor=RecordingConfig()
    )
    assert isinstance(result, PipelineFailure)
    assert result.error == "postprocessing failed"
    assert result.stages_completed == [PipelineStage.GENERATE, PipelineStage.RUN]
    assert isinstance(result.postprocess_results, PostprocessFailure)


def test_run_and_generate_results_are_typed_and_persist_failures_are_observable(tmp_path, monkeypatch):
    model = ModelRun(run_id="run-5", output_dir=tmp_path)
    with monkeypatch.context() as patch:
        patch.setattr(model.config.__class__, "render", lambda *_args, **_kwargs: None)
        generated = model.generate()
    assert isinstance(generated, GenerateSuccess)
    assert generated.timing.start_time.tzinfo is not None

    patch = pytest.MonkeyPatch()
    patch.setattr("rompy.core.result_persistence._atomic_write", Mock(side_effect=OSError("disk full")))
    try:
        failed = model.run(LocalConfig(command="exit 0", timeout=60), workspace_dir=str(model.staging_dir))
    finally:
        patch.undo()
    assert isinstance(failed, ModelRunFailure)
    assert failed.persistence_diagnostic is not None
    assert failed.persistence_diagnostic.error == "disk full"


def test_pipeline_strict_prefix_nested_failure_and_cleanup_precedence(tmp_path):
    generated = GenerateSuccess(run_id="run-5", staging_dir=str(tmp_path), generated_files=[], timing=timing())
    run = ModelRunFailure(
        run_id="run-5", backend_used="local", error="primary run failure", timing=timing(),
        output_dir=str(tmp_path), artifacts=[LocalArtifact(path="outputs/waves.nc")],
        expected_outputs=[LocalArtifact(path="outputs/waves.nc")], missing_outputs=[],
    )
    model = Mock(run_id="run-5", output_dir=tmp_path)
    model.generate.return_value = generated
    model.run.return_value = run
    model.postprocess = Mock(side_effect=AssertionError("postprocess must not run"))
    backend = LocalPipelineBackend()
    backend._cleanup_outputs = Mock(return_value=False)
    result = backend.execute(model, backend_config=LocalConfig(command="exit 0"), processor=RecordingConfig(), cleanup_on_failure=True)
    assert result.success is False
    assert result.failed_stage is PipelineStage.RUN
    assert result.stages_completed == [PipelineStage.GENERATE]
    assert result.stage_timings[-1].stage is PipelineStage.RUN
    assert result.error == "primary run failure"
    assert result.cleaned_up is False


def test_pipeline_postprocess_failure_retains_nested_evidence_and_prefix(tmp_path):
    generated = GenerateSuccess(run_id="run-5", staging_dir=str(tmp_path), generated_files=[], timing=timing())
    run = run_success(tmp_path)
    post = PostprocessFailure(
        run_id="run-5", error="postprocess failed", output_dir=str(tmp_path), timing=timing(),
        artifacts=run.artifacts, expected_outputs=run.expected_outputs, missing_outputs=[],
    )
    model = Mock(run_id="run-5", output_dir=tmp_path)
    model.generate.return_value = generated
    model.run.return_value = run
    model.postprocess.return_value = post
    backend = LocalPipelineBackend()
    result = backend.execute(model, backend_config=LocalConfig(command="exit 0"), processor=RecordingConfig())
    assert result.success is False
    assert result.failed_stage is PipelineStage.POSTPROCESS
    assert result.stages_completed == [PipelineStage.GENERATE, PipelineStage.RUN]
    assert result.postprocess_results is post
    assert [stage.stage for stage in result.stage_timings] == [PipelineStage.GENERATE, PipelineStage.RUN, PipelineStage.POSTPROCESS]
    assert result.error == "postprocess failed"


def test_backend_exception_after_implicit_generation_persists_failed_sidecar(tmp_path):
    class RaisingBackend:
        def run(self, model_run, config, workspace_dir=None):
            self.generate_result = model_run.generate()
            raise TimeoutError("backend timed out")

    model = ModelRun(run_id="run-5", output_dir=tmp_path)
    with patch.object(model.config.__class__, "render", return_value=None), \
         patch.object(LocalConfig, "get_backend_class", return_value=RaisingBackend):
        result = model.run(LocalConfig(command="true", timeout=60))

    assert isinstance(result, ModelRunFailure)
    assert result.error == "backend timed out"
    assert result.workspace_dir == str(model.staging_dir)
    persisted = load_run_result(model.staging_dir).payload
    assert isinstance(persisted, ModelRunFailure)
    assert persisted.error == "backend timed out"
    assert persisted.workspace_dir == str(model.staging_dir)
    assert persisted.metadata["normalized_context"]["staging_dir"] == str(model.staging_dir)


def test_run_result_context_survives_real_write_load_round_trip(tmp_path):
    model = ModelRun(run_id="run-5", output_dir=tmp_path)
    with patch.object(model.config.__class__, "render", return_value=None):
        generated = model.generate()
    result = model.run(LocalConfig(command="true", timeout=60), workspace_dir=generated.staging_dir)
    loaded = load_run_result(Path(generated.staging_dir)).payload
    assert result.metadata["normalized_context"] == loaded.metadata["normalized_context"]
    assert loaded.artifacts == result.artifacts
    assert loaded.expected_outputs == result.expected_outputs
    assert loaded.missing_outputs == result.missing_outputs


def test_cli_current_failure_envelope_preserves_persistence_and_primary_error(tmp_path):
    result = ModelRunFailure(
        run_id="run-5", backend_used="local", error="primary failed", timing=timing(),
        artifacts=[], expected_outputs=[], missing_outputs=[], output_dir=str(tmp_path),
        persistence_diagnostic=PersistenceDiagnostic(
            sidecar_kind="run_result", sidecar_path=str(tmp_path / "run_result.json"),
            error="permission denied", primary_error="primary failed",
        ),
    )
    envelope = _result_envelope(result, "run_result", staging_dir=tmp_path)
    assert envelope["success"] is False
    assert envelope["error"] == "primary failed"
    assert envelope["payload"]["persistence_diagnostic"]["error"] == "permission denied"
    assert envelope["payload"]["persistence_diagnostic"]["primary_error"] == "primary failed"


def test_pipeline_stage_exceptions_retain_typed_nested_failures(tmp_path):
    generated = GenerateSuccess(run_id="run-5", staging_dir=str(tmp_path), generated_files=[], timing=timing())
    model = Mock(run_id="run-5", output_dir=tmp_path, staging_dir=tmp_path)
    model.generate.side_effect = RuntimeError("generate primary")
    result = LocalPipelineBackend().execute(
        model, backend_config=LocalConfig(command="true"), processor=RecordingConfig()
    )
    assert result.failed_stage is PipelineStage.GENERATE
    assert isinstance(result.generate_result, GenerateFailure)
    assert result.generate_result.error == "generate primary"
    assert result.stage_timings[-1].stage is PipelineStage.GENERATE

    model = Mock(run_id="run-5", output_dir=tmp_path, staging_dir=tmp_path)
    model.generate.return_value = generated
    delay = 0.05

    def delayed_run(*_args, **_kwargs):
        time.sleep(delay)
        raise RuntimeError("run primary")

    model.run.side_effect = delayed_run
    result = LocalPipelineBackend().execute(
        model, backend_config=LocalConfig(command="true"), processor=RecordingConfig()
    )
    assert result.failed_stage is PipelineStage.RUN
    assert result.stages_completed == [PipelineStage.GENERATE]
    assert isinstance(result.run_result, ModelRunFailure)
    assert result.run_result.error == "run primary"
    assert result.run_result.timing.end_time >= result.run_result.timing.start_time
    assert result.run_result.timing.duration_seconds >= delay * 0.8
    run_stage_timing = result.stage_timings[-1].timing
    assert run_stage_timing.start_time == result.run_result.timing.start_time
    assert run_stage_timing.end_time == result.run_result.timing.end_time
    assert run_stage_timing.duration_seconds == result.run_result.timing.duration_seconds

    model = Mock(run_id="run-5", output_dir=tmp_path, staging_dir=tmp_path)
    model.generate.return_value = generated
    model.run.return_value = run_success(tmp_path)
    model.postprocess.side_effect = RuntimeError("postprocess primary")
    result = LocalPipelineBackend().execute(
        model, backend_config=LocalConfig(command="true"), processor=RecordingConfig()
    )
    assert result.failed_stage is PipelineStage.POSTPROCESS
    assert result.stages_completed == [PipelineStage.GENERATE, PipelineStage.RUN]
    assert isinstance(result.postprocess_results, PostprocessFailure)
    assert result.postprocess_results.error == "postprocess primary"


def test_pipeline_cleanup_exception_is_structured_without_masking_stage_error(tmp_path):
    generated = GenerateSuccess(run_id="run-5", staging_dir=str(tmp_path), generated_files=[], timing=timing())
    model = Mock(run_id="run-5", output_dir=tmp_path, staging_dir=tmp_path)
    model.generate.return_value = generated
    model.run.side_effect = RuntimeError("run primary")
    backend = LocalPipelineBackend()
    backend._cleanup_outputs = Mock(side_effect=OSError("cleanup secondary"))
    result = backend.execute(
        model, backend_config=LocalConfig(command="true"), processor=RecordingConfig(), cleanup_on_failure=True
    )
    assert result.error == "run primary"
    assert result.cleaned_up is False
    assert result.metadata["cleanup_error"] == "cleanup secondary"
    assert result.run_result.error == "run primary"


def test_cli_sidecar_input_preserves_typed_evidence(tmp_path):
    payload = run_success(tmp_path)
    sidecar = Mock(payload=payload)
    restored = _build_postprocess_processor_input(sidecar)
    assert restored is payload
    assert restored.artifacts == payload.artifacts
    assert TypeAdapter(ModelRunResult).validate_python(restored) == payload
