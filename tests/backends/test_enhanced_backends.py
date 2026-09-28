"""
Enhanced unit tests for the improved backend system with validation and error handling.

Tests cover the enhanced LocalRunBackend, NoopPostprocessor, and LocalPipelineBackend
with their new validation, error handling, and logging capabilities.
"""

import subprocess
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from rompy.backends import LocalConfig
from tests.test_helpers import DemoConfig
from rompy.core.time import TimeRange
from rompy.model import ModelRun
from rompy.pipeline import LocalPipelineBackend
from rompy.postprocess import NoopPostprocessor
from rompy.postprocess.config import NoopPostprocessorConfig
from rompy.run import LocalRunBackend
from rompy.core.responses import (
    Artifact,
    ArtifactType,
    PipelineFailure,
    PipelineStage,
    PipelineSuccess,
    PostprocessFailure,
    PostprocessSuccess,
    TimingInfo,
    GenerateFailure,
    GenerateSuccess,
    ModelRunSuccess,
    ModelRunFailure,
)


def generated_result(model_run, staging_dir, *, failure=False):
    now = datetime.now(timezone.utc)
    if failure:
        return GenerateFailure(
            run_id=model_run.run_id,
            error="generation failed",
            staging_dir=str(staging_dir),
            generated_files=[],
            timing=TimingInfo(start_time=now, end_time=now),
        )
    return GenerateSuccess(
        run_id=model_run.run_id,
        staging_dir=str(staging_dir),
        generated_files=[],
        timing=TimingInfo(start_time=now, end_time=now),
    )


def run_result(model_run, output_dir, *, failure=False):
    now = datetime.now(timezone.utc)
    common = dict(
        run_id=model_run.run_id,
        backend_used="local",
        output_dir=str(output_dir),
        workspace_dir=str(output_dir),
        artifacts=[],
        expected_outputs=[],
        missing_outputs=[],
        timing=TimingInfo(start_time=now, end_time=now),
    )
    if failure:
        return ModelRunFailure(error="run failed", **common)
    return ModelRunSuccess(**common)


@pytest.fixture
def model_run(tmp_path):
    """Create a basic ModelRun instance for testing."""
    return ModelRun(
        run_id="test_run",
        period=TimeRange(
            start=datetime(2020, 2, 21, 4),
            end=datetime(2020, 2, 24, 4),
            interval="15M",
        ),
        output_dir=str(tmp_path),
        config=DemoConfig(arg1="foo", arg2="bar"),
    )


@pytest.fixture
def model_run_with_run_method(tmp_path):
    """Create a ModelRun with a config that has a run method."""
    config = DemoConfig(arg1="foo", arg2="bar")
    config.run = MagicMock(return_value=True)

    return ModelRun(
        run_id="test_run_with_method",
        period=TimeRange(
            start=datetime(2020, 2, 21, 4),
            end=datetime(2020, 2, 24, 4),
            interval="15M",
        ),
        output_dir=str(tmp_path),
        config=config,
    )


@pytest.fixture
def processor_config():
    """Create a NoopPostprocessorConfig for testing."""
    return NoopPostprocessorConfig(validate_outputs=False)


@pytest.fixture
def backend_config():
    """Create a LocalConfig for testing."""
    return LocalConfig()


class TestEnhancedLocalRunBackend:
    """Test the enhanced LocalRunBackend with validation and error handling."""

    def test_run_validation_none_model_run(self):
        """Test validation when model_run is None."""
        backend = LocalRunBackend()
        config = LocalConfig()

        with pytest.raises(ValueError, match="model_run cannot be None"):
            backend.run(None, config)

    def test_run_validation_invalid_model_run(self):
        """Test that run raises ValueError for invalid model_run."""
        backend = LocalRunBackend()
        invalid_model = object()  # Object without run_id attribute
        config = LocalConfig()

        with pytest.raises(ValueError, match="model_run must have a run_id attribute"):
            backend.run(invalid_model, config)

    def test_run_with_command_success(self, model_run, tmp_path):
        """Test successful execution with custom command."""
        backend = LocalRunBackend()

        # Create output directory
        output_dir = tmp_path / model_run.run_id
        output_dir.mkdir(parents=True, exist_ok=True)

        config = LocalConfig(
            command="echo 'test output' > test_file.txt", working_dir=output_dir
        )

        with patch("rompy.model.ModelRun.generate", return_value=generated_result(model_run, output_dir)):
            result = backend.run(model_run, config)

        assert result is True
        assert (output_dir / "test_file.txt").exists()
        assert "test output" in (output_dir / "test_file.txt").read_text()

    def test_run_with_command_failure(self, model_run, tmp_path):
        """Test execution failure with custom command."""
        backend = LocalRunBackend()

        # Create output directory
        output_dir = tmp_path / model_run.run_id
        output_dir.mkdir(parents=True, exist_ok=True)

        config = LocalConfig(
            command="exit 1",
            working_dir=output_dir,  # Command that will fail
        )

        with patch("rompy.model.ModelRun.generate", return_value=generated_result(model_run, output_dir)):
            result = backend.run(model_run, config)

        assert result is False

    def test_run_with_command_timeout(self, model_run, tmp_path):
        """Test execution timeout with custom command."""
        backend = LocalRunBackend()

        # Create output directory
        output_dir = tmp_path / model_run.run_id
        output_dir.mkdir(parents=True, exist_ok=True)

        config = LocalConfig(
            command="sleep 10",  # Long running command
            timeout=60,  # Minimum allowed timeout
            working_dir=output_dir,
        )

        with patch("rompy.model.ModelRun.generate", return_value=generated_result(model_run, output_dir)):
            # Mock subprocess.run to raise TimeoutExpired
            with patch("subprocess.run") as mock_run:
                mock_run.side_effect = subprocess.TimeoutExpired("sleep 10", 60)
                with pytest.raises(TimeoutError, match="Command execution timed out"):
                    backend.run(model_run, config)

    def test_run_with_env_vars(self, model_run, tmp_path):
        """Test execution with environment variables."""
        backend = LocalRunBackend()

        output_dir = tmp_path / model_run.run_id
        output_dir.mkdir(parents=True, exist_ok=True)

        config = LocalConfig(
            command="echo $TEST_VAR > env_test.txt",
            env_vars={"TEST_VAR": "test_value"},
            working_dir=output_dir,
        )

        with patch("rompy.model.ModelRun.generate", return_value=generated_result(model_run, output_dir)):
            result = backend.run(model_run, config)

        assert result is True
        env_file = output_dir / "env_test.txt"
        assert env_file.exists()
        assert "test_value" in env_file.read_text()

    def test_run_with_config_run_method(self, model_run_with_run_method, tmp_path):
        """Test execution using config.run() method."""
        backend = LocalRunBackend()

        output_dir = tmp_path / model_run_with_run_method.run_id
        output_dir.mkdir(parents=True, exist_ok=True)

        config = LocalConfig(working_dir=output_dir)

        with patch("rompy.model.ModelRun.generate", return_value=generated_result(model_run_with_run_method, output_dir)):
            result = backend.run(model_run_with_run_method, config)

        assert result is True
        model_run_with_run_method.config.run.assert_called_once_with(
            model_run_with_run_method
        )

    def test_run_with_config_run_method_failure(
        self, model_run_with_run_method, tmp_path
    ):
        """Test execution failure using config.run() method."""
        backend = LocalRunBackend()

        output_dir = tmp_path / model_run_with_run_method.run_id
        output_dir.mkdir(parents=True, exist_ok=True)

        # Make config.run() raise an exception
        model_run_with_run_method.config.run.side_effect = Exception(
            "Config run failed"
        )

        config = LocalConfig(working_dir=output_dir)

        with patch("rompy.model.ModelRun.generate", return_value=generated_result(model_run_with_run_method, output_dir)):
            result = backend.run(model_run_with_run_method, config)

        assert result is False

    def test_run_with_nonexistent_working_dir(self, model_run, tmp_path):
        """Test execution with nonexistent working directory."""
        LocalRunBackend()

        nonexistent_dir = tmp_path / "nonexistent"

        # LocalConfig validation should catch this, but let's test runtime behavior
        with patch("rompy.model.ModelRun.generate", return_value=generated_result(model_run, tmp_path)):
            with pytest.raises(ValueError, match="Working directory does not exist"):
                LocalConfig(command="echo test", working_dir=nonexistent_dir)

    def test_execute_config_run_no_method(self, model_run, tmp_path):
        """Test _execute_config_run when config has no run method."""
        backend = LocalRunBackend()
        output_dir = tmp_path / "test"
        output_dir.mkdir()

        result = backend._execute_config_run(model_run, output_dir, {})

        # Should return True but log a warning
        assert result is True

    def test_execute_config_run_non_boolean_return(
        self, model_run_with_run_method, tmp_path
    ):
        """Test _execute_config_run when config.run() returns non-boolean."""
        backend = LocalRunBackend()
        output_dir = tmp_path / "test"
        output_dir.mkdir()

        # Make config.run() return a string instead of boolean
        model_run_with_run_method.config.run.return_value = "some_string"

        result = backend._execute_config_run(model_run_with_run_method, output_dir, {})

        # Should still return True but log a warning
        assert result is True


class TestEnhancedNoopPostprocessor:
    """Test the enhanced NoopPostprocessor with validation and error handling."""

    def test_process_validation_none_model_run(self):
        """Test that process returns PostprocessFailure for None model_run."""
        processor = NoopPostprocessor(NoopPostprocessorConfig(validate_outputs=False))

        result = processor.process(None)
        assert isinstance(result, PostprocessFailure)
        assert result.success is False
        assert "validated ModelRunResult" in result.error
        assert result.run_id == "unknown"

    def test_process_validation_invalid_model_run(self):
        """Test that process returns PostprocessFailure for invalid model_run."""
        processor = NoopPostprocessor(NoopPostprocessorConfig(validate_outputs=False))
        invalid_model = object()  # Object without run_id attribute

        result = processor.process(invalid_model)
        assert isinstance(result, PostprocessFailure)
        assert result.success is False
        assert "validated ModelRunResult" in result.error
        assert result.run_id == "unknown"

    def test_process_with_validation_success(self, model_run, tmp_path):
        """Test successful processing with output validation."""
        processor = NoopPostprocessor(NoopPostprocessorConfig(validate_outputs=False))

        # Create output directory with some files
        output_dir = tmp_path / model_run.run_id
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "output1.txt").write_text("test1")
        (output_dir / "output2.txt").write_text("test2")

        result = processor.process(run_result(model_run, output_dir), validate_outputs=True)

        # Verify result is PostprocessSuccess type
        assert isinstance(result, PostprocessSuccess)
        assert result.success is True
        assert result.run_id == model_run.run_id
        assert result.validated is True
        assert result.message is not None and "validation only" in result.message

        # Verify artifacts were tracked
        assert len(result.artifacts) == 2
        assert all(isinstance(artifact, Artifact) for artifact in result.artifacts)
        from pathlib import Path

        artifact_names = {Path(artifact.path).name for artifact in result.artifacts}
        assert artifact_names == {"output1.txt", "output2.txt"}

        # Verify timing information is present
        assert result.timing is not None
        assert result.timing.duration_seconds >= 0

    def test_process_with_validation_missing_dir(self, model_run, tmp_path):
        """Test processing with validation when output directory is missing."""
        processor = NoopPostprocessor(NoopPostprocessorConfig(validate_outputs=False))

        # Don't create output directory
        result = processor.process(
            run_result(model_run, tmp_path / model_run.run_id), validate_outputs=True
        )

        # Verify result is PostprocessFailure type
        assert isinstance(result, PostprocessFailure)
        assert result.success is False
        assert "not found" in result.error  # Check error field instead of message
        assert result.run_id == model_run.run_id

        # Verify timing information is present even on failure
        assert result.timing is not None
        assert result.timing.duration_seconds >= 0

    def test_process_without_validation(self, model_run, tmp_path):
        """Test processing without output validation."""
        processor = NoopPostprocessor(NoopPostprocessorConfig(validate_outputs=False))

        result = processor.process(
            run_result(model_run, tmp_path / model_run.run_id), validate_outputs=False
        )

        # Verify result is PostprocessSuccess type (no validation means success)
        assert isinstance(result, PostprocessSuccess)
        assert result.success is True
        assert result.run_id == model_run.run_id
        assert result.validated is False

        # Verify timing information is present
        assert result.timing is not None
        assert result.timing.duration_seconds >= 0

    def test_process_with_custom_output_dir(self, model_run, tmp_path):
        """Test processing with custom output directory."""
        processor = NoopPostprocessor(NoopPostprocessorConfig(validate_outputs=False))

        custom_dir = tmp_path / "custom_output"
        custom_dir.mkdir(parents=True, exist_ok=True)
        (custom_dir / "custom_file.txt").write_text("custom content")

        result = processor.process(
            run_result(model_run, custom_dir), validate_outputs=True, output_dir=str(custom_dir)
        )

        # Verify result is PostprocessSuccess type
        assert isinstance(result, PostprocessSuccess)
        assert result.success is True
        assert result.output_dir == str(custom_dir)

        # Verify artifacts from custom directory were tracked
        assert len(result.artifacts) == 1
        from pathlib import Path

        assert Path(result.artifacts[0].path).name == "custom_file.txt"
        assert result.artifacts[0].artifact_type == ArtifactType.TEXT

    def test_process_exception_handling(self, model_run):
        """Test exception handling in process method."""
        processor = NoopPostprocessor(NoopPostprocessorConfig(validate_outputs=False))

        # Mock Path to raise an exception
        with patch("rompy.postprocess.Path") as mock_path:
            mock_path.side_effect = Exception("File system error")

            result = processor.process(run_result(model_run, model_run.output_dir))

            # Verify result is PostprocessFailure type
            assert isinstance(result, PostprocessFailure)
            assert result.success is False
            assert result.error is not None
            assert (
                "File system error" in result.error
            )  # Check error field instead of message

            # Verify timing information is present even on exception
            assert result.timing is not None
            assert result.timing.duration_seconds >= 0


class TestEnhancedLocalPipelineBackend:
    """Test the enhanced LocalPipelineBackend with validation and error handling."""

    def test_execute_validation_none_model_run(self):
        """Test that execute raises ValueError for None model_run."""
        backend = LocalPipelineBackend()

        with pytest.raises(ValueError, match="model_run cannot be None"):
            backend.execute(None)

    def test_execute_validation_invalid_model_run(self):
        """Test that execute raises ValueError for invalid model_run."""
        backend = LocalPipelineBackend()
        invalid_model = object()  # Object without run_id attribute

        with pytest.raises(ValueError, match="model_run must have a run_id attribute"):
            backend.execute(invalid_model)

    def test_execute_validation_invalid_run_backend(self, model_run, processor_config):
        """Test that execute raises ValueError for invalid backend_config."""
        backend = LocalPipelineBackend()

        with pytest.raises(TypeError, match="must be a BaseBackendConfig instance"):
            backend.execute(
                model_run, backend_config="invalid", processor=processor_config
            )

    def test_execute_validation_invalid_processor(self, model_run, backend_config):
        """Test that execute raises TypeError for invalid processor type."""
        backend = LocalPipelineBackend()

        with pytest.raises(
            TypeError, match="must be a BasePostprocessorConfig instance"
        ):
            backend.execute(model_run, backend_config=backend_config, processor="noop")

    def test_execute_generate_failure(
        self, model_run, backend_config, processor_config
    ):
        """Test pipeline failure during generate stage."""
        backend = LocalPipelineBackend()

        with patch(
            "rompy.model.ModelRun.generate", side_effect=Exception("Generate failed")
        ):
            result = backend.execute(
                model_run, backend_config=backend_config, processor=processor_config
            )

        assert isinstance(result, PipelineFailure)
        assert result.success is False
        assert result.failed_stage == PipelineStage.GENERATE
        assert "Generate failed" in result.message
        assert PipelineStage.GENERATE not in result.stages_completed

    def test_execute_run_failure(
        self, model_run, tmp_path, backend_config, processor_config
    ):
        """Test pipeline failure during run stage."""
        backend = LocalPipelineBackend()

        output_dir = tmp_path / model_run.run_id
        output_dir.mkdir(parents=True, exist_ok=True)

        with patch("rompy.model.ModelRun.generate", return_value=generated_result(model_run, output_dir)):
            with patch("rompy.model.ModelRun.run", return_value=run_result(model_run, output_dir, failure=True)):
                result = backend.execute(
                    model_run, backend_config=backend_config, processor=processor_config
                )

        assert isinstance(result, PipelineFailure)
        assert result.success is False
        assert result.failed_stage == PipelineStage.RUN
        assert PipelineStage.GENERATE in result.stages_completed
        assert PipelineStage.RUN not in result.stages_completed

    def test_execute_run_exception(
        self, model_run, tmp_path, backend_config, processor_config
    ):
        """Test pipeline failure during run stage with exception."""
        backend = LocalPipelineBackend()

        output_dir = tmp_path / model_run.run_id
        output_dir.mkdir(parents=True, exist_ok=True)

        with patch("rompy.model.ModelRun.generate", return_value=generated_result(model_run, output_dir)):
            with patch("rompy.model.ModelRun.run", side_effect=Exception("Run failed")):
                result = backend.execute(
                    model_run, backend_config=backend_config, processor=processor_config
                )

        assert isinstance(result, PipelineFailure)
        assert result.success is False
        assert result.failed_stage == PipelineStage.RUN
        assert "Run failed" in result.message

    def test_execute_postprocess_failure(
        self, model_run, tmp_path, backend_config, processor_config
    ):
        """Test pipeline failure during postprocess stage."""
        backend = LocalPipelineBackend()

        output_dir = tmp_path / model_run.run_id
        output_dir.mkdir(parents=True, exist_ok=True)

        with patch("rompy.model.ModelRun.generate", return_value=generated_result(model_run, output_dir)):
            with patch(
                "rompy.model.ModelRun.run", return_value=run_result(model_run, output_dir)
            ):
                with patch(
                    "rompy.model.ModelRun.postprocess",
                    side_effect=Exception("Postprocess failed"),
                ):
                    result = backend.execute(
                        model_run,
                        backend_config=backend_config,
                        processor=processor_config,
                    )

        assert isinstance(result, PipelineFailure)
        assert result.success is False
        assert result.failed_stage == PipelineStage.POSTPROCESS
        assert PipelineStage.GENERATE in result.stages_completed
        assert PipelineStage.RUN in result.stages_completed
        assert PipelineStage.POSTPROCESS not in result.stages_completed

    def test_execute_success_complete(self, model_run, tmp_path, processor_config):
        """Test successful complete pipeline execution."""
        backend = LocalPipelineBackend()

        output_dir = tmp_path / model_run.run_id
        output_dir.mkdir(parents=True, exist_ok=True)

        # Create a PostprocessSuccess object for the mock
        from datetime import datetime, timezone

        mock_postprocess_result = PostprocessSuccess(
            run_id=model_run.run_id,
            output_dir=str(output_dir),
            validated=True,
            message="Postprocessing done",
            artifacts=[],
            expected_outputs=[],
            missing_outputs=[],
            timing=TimingInfo(
                start_time=datetime.now(timezone.utc),
                end_time=datetime.now(timezone.utc),
            ),
        )

        with patch("rompy.model.ModelRun.generate", return_value=generated_result(model_run, output_dir)):
            with patch(
                "rompy.model.ModelRun.run", return_value=run_result(model_run, output_dir)
            ):
                with patch(
                    "rompy.model.ModelRun.postprocess",
                    return_value=mock_postprocess_result,
                ):
                    result = backend.execute(
                        model_run,
                        backend_config=LocalConfig(),
                        processor=processor_config,
                        run_kwargs={"param1": "value1"},
                        process_kwargs={"param2": "value2"},
                    )

        assert isinstance(result, PipelineSuccess)
        assert result.success is True
        # If pipeline succeeded, run_success is implicitly True (no need to check separately)
        assert result.postprocess_results == mock_postprocess_result
        assert PipelineStage.GENERATE in result.stages_completed
        assert PipelineStage.RUN in result.stages_completed
        assert PipelineStage.POSTPROCESS in result.stages_completed
        assert result.message == "Pipeline completed successfully"

    def test_execute_with_validation_failure(
        self, model_run, tmp_path, backend_config, processor_config
    ):
        """Test pipeline with stage validation failure."""
        backend = LocalPipelineBackend()

        # Create generate result but not the actual directory
        with patch(
            "rompy.model.ModelRun.generate",
            return_value=generated_result(model_run, tmp_path / "nonexistent"),
        ):
            result = backend.execute(
                model_run,
                backend_config=backend_config,
                processor=processor_config,
                validate_stages=True,
            )

        assert isinstance(result, PipelineFailure)
        assert result.success is False
        assert result.failed_stage == PipelineStage.GENERATE
        assert "not found after generation" in result.message

    def test_execute_with_cleanup_on_failure(
        self, model_run, tmp_path, backend_config, processor_config
    ):
        """Test pipeline with cleanup on failure."""
        backend = LocalPipelineBackend()

        output_dir = tmp_path / model_run.run_id
        output_dir.mkdir(parents=True, exist_ok=True)
        test_file = output_dir / "test_file.txt"
        test_file.write_text("test content")

        with patch("rompy.model.ModelRun.generate", return_value=generated_result(model_run, output_dir)):
            with patch(
                "rompy.model.ModelRun.run", return_value=run_result(model_run, output_dir, failure=True)
            ):
                result = backend.execute(
                    model_run,
                    backend_config=backend_config,
                    processor=processor_config,
                    cleanup_on_failure=True,
                )

        assert isinstance(result, PipelineFailure)
        assert result.success is False
        assert result.cleaned_up is True
        # Directory should be cleaned up
        assert not output_dir.exists()

    def test_cleanup_outputs_success(self, model_run, tmp_path):
        """Test successful cleanup of output directory."""
        backend = LocalPipelineBackend()

        # Create output directory with files
        output_dir = tmp_path / model_run.run_id
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "file1.txt").write_text("content1")
        (output_dir / "file2.txt").write_text("content2")

        model_run.output_dir = tmp_path

        backend._cleanup_outputs(output_dir)

        assert not output_dir.exists()

    def test_cleanup_outputs_failure(self, model_run, tmp_path):
        """Test cleanup failure handling."""
        backend = LocalPipelineBackend()

        model_run.output_dir = tmp_path

        # Mock shutil.rmtree to raise an exception
        with patch("shutil.rmtree", side_effect=Exception("Permission denied")):
            # Should not raise exception, just log warning
            backend._cleanup_outputs(model_run)

    def test_execute_postprocess_warning_on_failure(
        self, model_run, tmp_path, backend_config, processor_config
    ):
        """Test pipeline returns failure when postprocessing reports failure but doesn't raise."""
        backend = LocalPipelineBackend()

        output_dir = tmp_path / model_run.run_id
        output_dir.mkdir(parents=True, exist_ok=True)

        # Postprocessor returns PostprocessFailure but doesn't raise exception
        from datetime import datetime, timezone

        start = datetime.now(timezone.utc)
        end = datetime.now(timezone.utc)

        mock_postprocess_result = PostprocessFailure(
            run_id=model_run.run_id,
            error="Postprocessing had issues",
            message="Postprocessing had issues",
            artifacts=[], expected_outputs=[], missing_outputs=[],
            timing=TimingInfo(start_time=start, end_time=end),
        )

        with patch("rompy.model.ModelRun.generate", return_value=generated_result(model_run, output_dir)):
            with patch(
                "rompy.model.ModelRun.run", return_value=run_result(model_run, output_dir)
            ):
                with patch(
                    "rompy.model.ModelRun.postprocess",
                    return_value=mock_postprocess_result,
                ):
                    result = backend.execute(
                        model_run,
                        backend_config=backend_config,
                        processor=processor_config,
                    )

        # Pipeline should return failure when postprocessing fails
        # (even if it doesn't raise an exception)
        assert isinstance(result, PipelineFailure)
        assert result.success is False
        assert result.failed_stage == PipelineStage.POSTPROCESS
        assert result.postprocess_results == mock_postprocess_result
        assert "Postprocessing had issues" in result.error
        assert result.postprocess_results == mock_postprocess_result
        assert PipelineStage.POSTPROCESS not in result.stages_completed
