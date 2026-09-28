"""
Integration tests for ModelRun with the new Pydantic backend system.

These tests verify that the ModelRun.run() method works correctly with
BackendConfig instances instead of the old string-based backend system.
"""

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from rompy.backends import DockerConfig, LocalConfig
from rompy.core.responses import (
    Artifact,
    GenerateSuccess,
    ModelRunFailure,
    ModelRunSuccess,
    TimingInfo,
)
from rompy.core.result_persistence import load_run_result
from rompy.core.time import TimeRange
from rompy.model import ModelRun
from tests.test_helpers import DemoConfig

ModelRunResult = (ModelRunSuccess, ModelRunFailure)


def typed_generation(path):
    now = datetime.now(timezone.utc)
    return GenerateSuccess(run_id="test_run", staging_dir=str(path), generated_files=[], timing=TimingInfo(start_time=now, end_time=now))


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


class TestModelRunPydanticIntegration:
    """Test ModelRun.run() with the new Pydantic backend system."""

    def test_run_with_local_config(self, model_run, tmp_path):
        """Test ModelRun.run() with LocalConfig instance."""
        # Create output directory
        output_dir = tmp_path / model_run.run_id
        output_dir.mkdir(parents=True, exist_ok=True)

        # Create LocalConfig
        config = LocalConfig(
            command="echo 'test output' > test_file.txt",
            working_dir=output_dir,
            timeout=3600,
        )

        with patch("rompy.model.ModelRun.generate", return_value=typed_generation(output_dir)):
            result = model_run.run(backend=config)

        assert result.success is True
        assert (output_dir / "test_file.txt").exists()
        assert "test output" in (output_dir / "test_file.txt").read_text()

    def test_run_with_local_config_using_config_run_method(
        self, model_run_with_run_method, tmp_path
    ):
        """Test ModelRun.run() with LocalConfig that uses config.run() method."""
        # Create output directory
        output_dir = tmp_path / model_run_with_run_method.run_id
        output_dir.mkdir(parents=True, exist_ok=True)

        # Create LocalConfig without command (will use config.run())
        config = LocalConfig(working_dir=output_dir)

        with patch("rompy.model.ModelRun.generate", return_value=typed_generation(output_dir)):
            result = model_run_with_run_method.run(backend=config)

        assert result.success is True
        # Verify config.run() was called
        model_run_with_run_method.config.run.assert_called_once_with(
            model_run_with_run_method
        )

    def test_run_with_docker_config(self, model_run, tmp_path):
        """Test ModelRun.run() with DockerConfig instance."""
        # Mock DockerRunBackend since we don't want to actually run Docker
        with patch("rompy.run.docker.DockerRunBackend") as mock_docker_backend_class:
            mock_backend_instance = MagicMock()
            mock_backend_instance.run.return_value = True
            mock_docker_backend_class.return_value = mock_backend_instance

            # Create DockerConfig
            config = DockerConfig(
                image="test-image:latest", cpu=2, memory="1g", timeout=7200
            )

            result = model_run.run(backend=config)

            assert result.success is True
            # Verify DockerRunBackend was instantiated and called
            mock_docker_backend_class.assert_called_once()
            mock_backend_instance.run.assert_called_once_with(
                model_run, config=config, workspace_dir=None
            )

    def test_run_converts_path_workspace_dir_to_string(self, model_run, tmp_path):
        """Test Path workspace_dir is normalized to string in ModelRunResult."""
        output_dir = tmp_path / model_run.run_id
        output_dir.mkdir(parents=True, exist_ok=True)

        config = LocalConfig(
            command="echo test",
            working_dir=output_dir,
        )

        with patch("rompy.model.ModelRun.generate", return_value=typed_generation(output_dir)):
            result = model_run.run(backend=config, workspace_dir=output_dir)

        assert result.success is True
        assert result.workspace_dir == str(output_dir)

    def test_run_with_invalid_backend_type(self, model_run):
        """Test ModelRun.run() returns failure result for invalid backend types."""
        # Invalid types should return ModelRunResult with success=False (not raise)
        result = model_run.run(backend="invalid_string")
        assert isinstance(result, ModelRunResult)
        assert result.success is False
        assert "BaseBackendConfig" in result.error

        result = model_run.run(backend={"invalid": "dict"})
        assert isinstance(result, ModelRunResult)
        assert result.success is False
        assert "BaseBackendConfig" in result.error

        result = model_run.run(backend=123)
        assert isinstance(result, ModelRunResult)
        assert result.success is False
        assert "BaseBackendConfig" in result.error

    def test_run_with_local_config_env_vars(self, model_run, tmp_path):
        """Test ModelRun.run() with LocalConfig and environment variables."""
        # Create output directory
        output_dir = tmp_path / model_run.run_id
        output_dir.mkdir(parents=True, exist_ok=True)

        # Create LocalConfig with environment variables
        config = LocalConfig(
            command="echo $TEST_VAR > env_test.txt",
            working_dir=output_dir,
            env_vars={"TEST_VAR": "hello_world"},
        )

        with patch("rompy.model.ModelRun.generate", return_value=typed_generation(output_dir)):
            result = model_run.run(backend=config)

        assert result.success is True
        env_file = output_dir / "env_test.txt"
        assert env_file.exists()
        assert "hello_world" in env_file.read_text()

    def test_run_backend_failure_propagation(self, model_run, tmp_path):
        """Test that backend failures are properly propagated."""
        # Create output directory
        output_dir = tmp_path / model_run.run_id
        output_dir.mkdir(parents=True, exist_ok=True)

        # Create LocalConfig with failing command
        config = LocalConfig(
            command="exit 1",
            working_dir=output_dir,  # Command that will fail
        )

        with patch("rompy.model.ModelRun.generate", return_value=typed_generation(output_dir)):
            result = model_run.run(backend=config)

        assert result.success is False

    def test_run_backend_exception_handling(self, model_run):
        """Test that backend exceptions are handled gracefully."""
        # Mock LocalRunBackend to raise an exception
        with patch("rompy.run.LocalRunBackend") as mock_backend_class:
            mock_backend_instance = MagicMock()
            mock_backend_instance.run.side_effect = Exception("Backend error")
            mock_backend_class.return_value = mock_backend_instance

            config = LocalConfig()

            # Exception should be caught and wrapped in ModelRunResult
            result = model_run.run(backend=config)
            assert isinstance(result, ModelRunResult)
            assert result.success is False
            assert "Backend error" in result.error

    def test_local_config_validation_in_modelrun_context(self, model_run, tmp_path):
        """Test LocalConfig validation works in ModelRun context."""
        # Test timeout validation
        with pytest.raises(
            ValueError, match="Input should be greater than or equal to 60"
        ):
            LocalConfig(timeout=30)  # Below minimum

        # Test working directory validation
        nonexistent_dir = tmp_path / "nonexistent"
        with pytest.raises(ValueError, match="Working directory does not exist"):
            LocalConfig(working_dir=nonexistent_dir)

        # Test valid config creation
        valid_dir = tmp_path / "valid"
        valid_dir.mkdir()
        config = LocalConfig(working_dir=valid_dir, timeout=3600)
        assert config.working_dir == valid_dir
        assert config.timeout == 3600

    def test_docker_config_validation_in_modelrun_context(self, model_run, tmp_path):
        """Test DockerConfig validation works in ModelRun context."""
        # Test image validation
        config = DockerConfig(image="valid-image:tag")
        assert config.image == "valid-image:tag"

        # Test dockerfile validation
        dockerfile = Path("Dockerfile")
        dockerfile_full_path = tmp_path / "Dockerfile"
        dockerfile_full_path.write_text("FROM python:3.9")
        config = DockerConfig(dockerfile=dockerfile, build_context=tmp_path)
        assert config.dockerfile == dockerfile

        # Test image or dockerfile requirement
        with pytest.raises(
            ValueError, match="Either 'image' or 'dockerfile' must be provided"
        ):
            DockerConfig()

        # Test mutual exclusion of image and dockerfile
        with pytest.raises(
            ValueError, match="Cannot specify both 'image' and 'dockerfile'"
        ):
            DockerConfig(image="test:latest", dockerfile=dockerfile)

    def test_backend_config_type_safety(self, model_run):
        """Test that the backend config system provides proper type safety."""
        # LocalConfig should work
        local_config = LocalConfig(command="echo test")
        assert isinstance(local_config, LocalConfig)
        assert local_config.get_backend_class().__name__ == "LocalRunBackend"

        # DockerConfig should work
        docker_config = DockerConfig(image="test:latest")
        assert isinstance(docker_config, DockerConfig)
        assert docker_config.get_backend_class().__name__ == "DockerRunBackend"

        # Both should be BackendConfig instances
        from rompy.backends import BackendConfig

        assert isinstance(local_config, BackendConfig)
        assert isinstance(docker_config, BackendConfig)

    def test_run_success(self, model_run, tmp_path):
        """Test ModelRun.run() returns ModelRunResult on success."""
        # Create output directory
        output_dir = tmp_path / model_run.run_id
        output_dir.mkdir(parents=True, exist_ok=True)

        config = LocalConfig(
            command="echo 'test output' > test_file.txt",
            working_dir=output_dir,
            timeout=3600,
        )

        with patch("rompy.model.ModelRun.generate", return_value=typed_generation(output_dir)):
            result = model_run.run(backend=config)

        # Verify result type
        assert isinstance(result, ModelRunResult)
        assert result.success is True
        assert result.run_id == model_run.run_id
        assert result.backend_used == "Local"

        # Verify timing information
        assert result.timing is not None
        assert result.timing.duration_seconds >= 0

        # Verify output directory
        assert result.output_dir is not None

        # Verify metadata
        assert result.metadata is not None
        assert "backend_config" in result.metadata

    def test_run_failure(self, model_run, tmp_path):
        """Test ModelRun.run() returns failure result on error."""
        config = LocalConfig(
            command="exit 1",  # Command that fails
            working_dir=tmp_path,
        )

        with patch("rompy.model.ModelRun.generate", return_value=typed_generation(tmp_path)):
            with patch(
                "rompy.run.LocalRunBackend.run",
                return_value=False,  # Simulate failure
            ):
                result = model_run.run(backend=config)

        # Verify result type
        assert isinstance(result, ModelRunResult)
        assert result.success is False
        assert result.run_id == model_run.run_id
        assert result.message == "Model execution failed"

        # Verify timing even on failure
        assert result.timing is not None
        assert result.timing.duration_seconds >= 0

    def test_run_invalid_backend(self, model_run):
        """Test ModelRun.run() handles invalid backend type."""
        # Pass invalid backend type (string instead of config)
        result = model_run.run(backend="invalid")

        # Should return failure result, not raise exception
        assert isinstance(result, ModelRunResult)
        assert result.success is False
        assert "BaseBackendConfig" in result.error
        assert result.timing is not None

    def test_run_exception_handling(self, model_run):
        """Test ModelRun.run() handles exceptions from the backend gracefully."""
        config = LocalConfig(command="echo test")

        # Patch the backend's run() so the outer ModelRun.run() catches the exception
        with patch(
            "rompy.run.LocalRunBackend.run",
            side_effect=RuntimeError("Simulated backend error"),
        ):
            result = model_run.run(backend=config)

        # Should return failure result with error details
        assert isinstance(result, ModelRunResult)
        assert result.success is False
        assert "Simulated backend error" in result.error
        assert "exception" in result.message.lower()
        assert result.timing is not None

    def test_run_timing_accuracy(self, model_run, tmp_path):
        """Test that run() captures accurate timing information."""

        output_dir = tmp_path / model_run.run_id
        output_dir.mkdir(parents=True, exist_ok=True)

        config = LocalConfig(
            command="sleep 0.1",  # Small delay to measure
            working_dir=output_dir,
        )

        with patch("rompy.model.ModelRun.generate", return_value=typed_generation(output_dir)):
            result = model_run.run(backend=config)

        # Verify timing was captured
        assert result.timing.duration_seconds >= 0.05  # At least some time passed
        assert result.timing.start_time < result.timing.end_time

    def test_run_metadata_includes_config(self, model_run, tmp_path):
        """Test that run() includes backend config in metadata."""
        output_dir = tmp_path / model_run.run_id
        output_dir.mkdir(parents=True, exist_ok=True)

        config = LocalConfig(
            command="echo test",
            working_dir=output_dir,
            timeout=7200,
        )

        with patch("rompy.model.ModelRun.generate", return_value=typed_generation(output_dir)):
            result = model_run.run(backend=config)

        # Verify metadata contains backend config
        assert result.metadata is not None
        assert "backend_config" in result.metadata
        backend_config_dict = result.metadata["backend_config"]
        assert backend_config_dict == {"type": "LocalConfig", "timeout": 7200}

    def test_run_metadata_redacts_backend_secrets(self, model_run, tmp_path):
        """Persisted run metadata contains no environment or build credentials."""
        output_dir = tmp_path / model_run.run_id
        output_dir.mkdir(parents=True, exist_ok=True)
        local = LocalConfig(
            command="true",
            working_dir=output_dir,
            env_vars={"API_TOKEN": "env-token-secret", "PASSWORD": "env-password-secret"},
        )
        with patch("rompy.model.ModelRun.generate", return_value=typed_generation(output_dir)):
            result = model_run.run(backend=local, workspace_dir=output_dir)

        raw = (output_dir / "run_result.json").read_text()
        assert result.metadata["backend_config"] == {"type": "LocalConfig", "timeout": 3600}
        assert "env-token-secret" not in raw
        assert "env-password-secret" not in raw
        assert "env_vars" not in raw

        docker = DockerConfig(
            image="test-image:latest",
            build_args={"TOKEN": "docker-token-secret", "PASSWORD": "docker-password-secret"},
        )
        with patch("rompy.run.docker.DockerRunBackend") as backend_class:
            backend_class.return_value.run.return_value = True
            backend_class.return_value.generate_result = None
            result = model_run.run(backend=docker, workspace_dir=output_dir)

        raw = (output_dir / "run_result.json").read_text()
        assert result.metadata["backend_config"] == {"type": "DockerConfig", "timeout": 3600}
        assert "docker-token-secret" not in raw
        assert "docker-password-secret" not in raw
        assert "build_args" not in raw
        loaded = load_run_result(output_dir)
        assert loaded.payload.metadata["backend_config"] == result.metadata["backend_config"]

    def test_run_success_populates_artifacts_from_validate_outputs(
        self, model_run, tmp_path
    ):
        """Test successful run includes artifacts from config.validate_outputs()."""
        output_dir = tmp_path / model_run.run_id
        output_dir.mkdir(parents=True, exist_ok=True)

        config = LocalConfig(
            command="echo test",
            working_dir=output_dir,
        )
        discovered = [Artifact(path="result.nc")]

        with patch("rompy.model.ModelRun.generate", return_value=typed_generation(output_dir)):
            with patch.object(
                DemoConfig, "validate_outputs", return_value=discovered
            ) as mock_validate:
                result = model_run.run(backend=config)

        assert result.success is True
        # Canonical artifact identities are already staging-relative.
        expected = discovered
        assert result.artifacts == expected
        # validate_outputs should be called with the actual run output
        # directory (including the run_id subdirectory in this test).
        mock_validate.assert_called_once_with(str(output_dir))

    def test_run_success_normalizes_artifact_paths_to_run_output_dir(
        self, model_run, tmp_path
    ):
        output_root = tmp_path / "outputs"
        run_output_dir = output_root / model_run.run_id
        run_output_dir.mkdir(parents=True, exist_ok=True)

        config = LocalConfig(
            command="echo test",
            working_dir=run_output_dir,
        )
        discovered = [
            Artifact(path="result.nc"),
            Artifact(path="nested/plot.png"),
        ]
        model_run.output_dir = output_root

        with patch("rompy.model.ModelRun.generate", return_value=typed_generation(run_output_dir)):
            with patch.object(
                DemoConfig, "validate_outputs", return_value=discovered
            ) as mock_validate:
                result = model_run.run(backend=config)

        assert result.success is True
        assert [artifact.path for artifact in result.artifacts] == [
            "result.nc",
            "nested/plot.png",
        ]
        mock_validate.assert_called_once_with(str(run_output_dir))

    def test_run_failure_does_not_validate_outputs(self, model_run, tmp_path):
        """Test failed run does not call config.validate_outputs()."""
        output_dir = tmp_path / model_run.run_id
        output_dir.mkdir(parents=True, exist_ok=True)

        config = LocalConfig(
            command="exit 1",
            working_dir=output_dir,
        )

        with patch("rompy.model.ModelRun.generate", return_value=typed_generation(output_dir)):
            with patch(
                "rompy.run.LocalRunBackend.run",
                return_value=False,
            ):
                with patch.object(DemoConfig, "validate_outputs") as mock_validate:
                    result = model_run.run(backend=config)

        assert result.success is False
        assert result.artifacts == []
        mock_validate.assert_not_called()
