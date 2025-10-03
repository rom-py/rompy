"""
Integration tests for the Docker backend.

These tests require Docker to be installed and running.
They test the full Docker backend functionality with real containers.
"""

import subprocess
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest
import docker
from docker.errors import APIError

from rompy.backends.config import DockerConfig
from rompy.core.config import BaseConfig
from rompy.core.time import TimeRange
from rompy.model import ModelRun
from rompy.run.docker import DockerRunBackend


def docker_available():
    """Check if Docker is available and running."""
    try:
        client = docker.from_env()
        client.ping()
        return True
    except (APIError, docker.errors.DockerException):
        return False


@pytest.fixture
def model_run(tmp_path):
    """Create a basic ModelRun instance for testing."""
    return ModelRun(
        run_id="test_docker_run",
        period=TimeRange(
            start=datetime(2020, 2, 21, 4),
            end=datetime(2020, 2, 24, 4),
            interval="15M",
        ),
        output_dir=str(tmp_path),
        config=BaseConfig(arg1="foo", arg2="bar"),
    )


@pytest.fixture
def docker_backend():
    """Create a DockerRunBackend instance."""
    return DockerRunBackend()


class TestDockerBackendIntegration:
    """Integration tests for Docker backend with real containers."""

    @pytest.mark.skipif(not docker_available(), reason="Docker not available")
    def test_run_with_simple_image(self, model_run, docker_backend, tmp_path):
        """Test running with a simple Docker image."""
        # Create a simple test file in the output directory
        output_dir = tmp_path / model_run.run_id
        output_dir.mkdir(parents=True, exist_ok=True)
        test_file = output_dir / "test_input.txt"
        test_file.write_text("test content")

        # Create DockerConfig
        config = DockerConfig(
            image="ubuntu:20.04", executable="echo 'Docker test successful'", cpu=1
        )

        # Mock the generate method to avoid template rendering
        with patch("rompy.model.ModelRun.generate", return_value=str(output_dir)):
            result = docker_backend.run(model_run, config)

        assert result is True

    @pytest.mark.skipif(not docker_available(), reason="Docker not available")
    def test_run_with_custom_command(self, model_run, docker_backend, tmp_path):
        """Test running with a custom command that creates output."""
        output_dir = tmp_path / model_run.run_id
        output_dir.mkdir(parents=True, exist_ok=True)

        # Create DockerConfig
        config = DockerConfig(
            image="ubuntu:20.04",
            executable="sh -c 'echo Docker test output > docker_test.txt'",
            cpu=1,
        )

        # Mock the generate method
        with patch("rompy.model.ModelRun.generate", return_value=str(output_dir)):
            result = docker_backend.run(model_run, config)

        assert result is True

        # Check if the output file was created
        output_file = output_dir / "docker_test.txt"
        assert output_file.exists()
        assert "Docker test output" in output_file.read_text()

    @pytest.mark.skipif(not docker_available(), reason="Docker not available")
    def test_run_with_environment_variables(self, model_run, docker_backend, tmp_path):
        """Test running with custom environment variables."""
        output_dir = tmp_path / model_run.run_id
        output_dir.mkdir(parents=True, exist_ok=True)

        # Create DockerConfig
        config = DockerConfig(
            image="ubuntu:20.04",
            executable="sh -c 'echo $TEST_VAR > env_test.txt'",
            env_vars={
                "TEST_VAR": "test_value",
                "ANOTHER_VAR": "another_value",
            },
            cpu=1,
        )

        # Mock the generate method
        with patch("rompy.model.ModelRun.generate", return_value=str(output_dir)):
            result = docker_backend.run(model_run, config)

        assert result is True

        # Check if environment variable was used
        env_file = output_dir / "env_test.txt"
        assert env_file.exists()
        assert "test_value" in env_file.read_text()

    @pytest.mark.skipif(not docker_available(), reason="Docker not available")
    def test_run_with_additional_volumes(self, model_run, docker_backend, tmp_path):
        """Test running with additional volume mounts."""
        output_dir = tmp_path / model_run.run_id
        output_dir.mkdir(parents=True, exist_ok=True)

        # Create an additional directory to mount
        extra_dir = tmp_path / "extra_data"
        extra_dir.mkdir()
        extra_file = extra_dir / "extra_file.txt"
        extra_file.write_text("extra data")

        # Create DockerConfig
        config = DockerConfig(
            image="ubuntu:20.04",
            executable="sh -c 'cat /extra/extra_file.txt > volume_test.txt'",
            volumes=[f"{extra_dir}:/extra:Z"],
            cpu=1,
        )

        # Mock the generate method
        with patch("rompy.model.ModelRun.generate", return_value=str(output_dir)):
            result = docker_backend.run(model_run, config)

        assert result is True

        # Check if volume mount worked
        volume_file = output_dir / "volume_test.txt"
        assert volume_file.exists()
        assert "extra data" in volume_file.read_text()

    def test_run_with_invalid_image(self, model_run, docker_backend, tmp_path):
        """Test running with an invalid Docker image."""
        output_dir = tmp_path / model_run.run_id
        output_dir.mkdir(parents=True, exist_ok=True)

        # Create DockerConfig
        config = DockerConfig(image="nonexistent:image", executable="echo", cpu=1)

        # Mock the generate method
        with patch("rompy.model.ModelRun.generate", return_value=str(output_dir)):
            result = docker_backend.run(model_run, config)

        # Should return False for invalid image
        assert result is False

    def test_prepare_image_with_existing_image(self, docker_backend):
        """Test _prepare_image with an existing image name."""
        result = docker_backend._prepare_image("ubuntu:20.04", None)
        assert result == "ubuntu:20.04"

    def test_prepare_image_with_dockerfile(self, docker_backend, tmp_path):
        """Test _prepare_image with a Dockerfile."""
        # Create a build context with Dockerfile
        context_dir = tmp_path / "build_context"
        context_dir.mkdir()
        dockerfile = context_dir / "Dockerfile"
        dockerfile.write_text(
            """
FROM ubuntu:20.04
RUN echo "test dockerfile"
"""
        )

        # Mock docker.from_env to avoid actually building
        with patch("docker.from_env") as mock_docker:
            mock_client = mock_docker.return_value
            mock_client.images.build.return_value = (
                "image_object",
                [{"stream": "Successfully built image"}],
            )

            # Mock _image_exists to return False (image doesn't exist)
            with patch.object(docker_backend, "_image_exists", return_value=False):
                result = docker_backend._prepare_image(
                    None, "Dockerfile", str(context_dir)
                )

                # Should return a generated image name
                assert result.startswith("rompy-")
                mock_client.images.build.assert_called_once()

    def test_prepare_image_with_dockerfile_build_failure(
        self, docker_backend, tmp_path
    ):
        """Test _prepare_image with a Dockerfile that fails to build."""
        context_dir = tmp_path / "build_context"
        context_dir.mkdir()
        dockerfile = context_dir / "Dockerfile"
        dockerfile.write_text("INVALID DOCKERFILE CONTENT")

        # Mock docker.from_env to simulate build failure
        with patch("docker.from_env") as mock_docker:
            mock_client = mock_docker.return_value
            mock_client.images.build.side_effect = docker.errors.BuildError(
                "Build failed", []
            )

            # Mock _image_exists to return False (image doesn't exist)
            with patch.object(docker_backend, "_image_exists", return_value=False):
                result = docker_backend._prepare_image(
                    None, "Dockerfile", str(context_dir)
                )

                # Should return None on build failure
                assert result is None

    def test_prepare_image_with_build_context(self, docker_backend, tmp_path):
        """Test _prepare_image with custom build context."""
        # Create a Dockerfile and build context
        context_dir = tmp_path / "build_context"
        context_dir.mkdir()
        dockerfile = context_dir / "Dockerfile"
        dockerfile.write_text(
            """
FROM ubuntu:20.04
COPY test.txt /app/
"""
        )

        # Create a file in the build context
        test_file = context_dir / "test.txt"
        test_file.write_text("test content")

        # Mock docker.from_env to avoid actually building
        with patch("docker.from_env") as mock_docker:
            mock_client = mock_docker.return_value
            mock_client.images.build.return_value = (
                "image_object",
                [{"stream": "Successfully built image"}],
            )

            # Mock _image_exists to return False (image doesn't exist)
            with patch.object(docker_backend, "_image_exists", return_value=False):
                result = docker_backend._prepare_image(
                    None, str(dockerfile), str(context_dir)
                )

                # Should return a generated image name
                assert result.startswith("rompy-")

                # Check that docker.images.build was called with correct context
                mock_client.images.build.assert_called_once()
                call_kwargs = mock_client.images.build.call_args[1]
                assert call_kwargs["path"] == str(context_dir)

    def test_prepare_image_with_existing_image(self, docker_backend, tmp_path):
        """Test _prepare_image with an image that already exists."""
        context_dir = tmp_path / "build_context"
        context_dir.mkdir()
        dockerfile = context_dir / "Dockerfile"
        dockerfile.write_text(
            """
FROM ubuntu:20.04
RUN echo "test dockerfile"
"""
        )

        # Mock _image_exists to return True (image already exists)
        with patch.object(docker_backend, "_image_exists", return_value=True):
            # Mock docker.from_env to ensure it's NOT called
            with patch("docker.from_env") as mock_docker:
                result = docker_backend._prepare_image(
                    None, "Dockerfile", str(context_dir)
                )

                # Should return the existing image name
                assert result.startswith("rompy-")
                # Build should not be called since image exists
                mock_docker.assert_not_called()

    def test_generate_image_name_deterministic(self, docker_backend, tmp_path):
        """Test that _generate_image_name produces deterministic results."""
        context_dir = tmp_path / "build_context"
        context_dir.mkdir()
        dockerfile = context_dir / "Dockerfile"
        dockerfile.write_text(
            """
FROM ubuntu:20.04
RUN echo "test"
"""
        )

        build_args = {"ARG1": "value1", "ARG2": "value2"}

        # Generate image name twice with same inputs
        name1 = docker_backend._generate_image_name(dockerfile, context_dir, build_args)
        name2 = docker_backend._generate_image_name(dockerfile, context_dir, build_args)

        # Should be identical
        assert name1 == name2
        assert name1.startswith("rompy-")
        assert len(name1.split("-")[1]) == 12  # 12-character hash

    def test_generate_image_name_different_content(self, docker_backend, tmp_path):
        """Test that _generate_image_name produces different names for different content."""
        context_dir = tmp_path / "build_context"
        context_dir.mkdir()

        dockerfile1 = context_dir / "Dockerfile1"
        dockerfile1.write_text("FROM ubuntu:20.04\nRUN echo 'test1'")

        dockerfile2 = context_dir / "Dockerfile2"
        dockerfile2.write_text("FROM ubuntu:20.04\nRUN echo 'test2'")

        name1 = docker_backend._generate_image_name(dockerfile1, context_dir)
        name2 = docker_backend._generate_image_name(dockerfile2, context_dir)

        # Should be different
        assert name1 != name2
        assert name1.startswith("rompy-")
        assert name2.startswith("rompy-")

    def test_generate_image_name_different_build_args(self, docker_backend, tmp_path):
        """Test that _generate_image_name produces different names for different build args."""
        context_dir = tmp_path / "build_context"
        context_dir.mkdir()
        dockerfile = context_dir / "Dockerfile"
        dockerfile.write_text("FROM ubuntu:20.04\nRUN echo 'test'")

        build_args1 = {"ARG1": "value1"}
        build_args2 = {"ARG1": "value2"}

        name1 = docker_backend._generate_image_name(
            dockerfile, context_dir, build_args1
        )
        name2 = docker_backend._generate_image_name(
            dockerfile, context_dir, build_args2
        )

        # Should be different
        assert name1 != name2

    def test_generate_image_name_unreadable_dockerfile(self, docker_backend, tmp_path):
        """Test _generate_image_name with unreadable Dockerfile."""
        context_dir = tmp_path / "build_context"
        context_dir.mkdir()
        dockerfile = context_dir / "nonexistent.dockerfile"

        # Should fallback to timestamp-based naming
        name = docker_backend._generate_image_name(dockerfile, context_dir)
        assert name.startswith("rompy-")
        # Timestamp-based name should be different from hash-based name format
        # Hash-based names are 12 chars after prefix (rompy-123456789012 = 18 total)
        # Timestamp-based names are ~10 chars after prefix (rompy-1234567890 = 16 total)
        assert len(name) < len("rompy-123456789012")
        assert len(name) >= len("rompy-1234567890")

    def test_image_exists_true(self, docker_backend):
        """Test _image_exists when image exists."""
        with patch("docker.from_env") as mock_docker:
            mock_client = mock_docker.return_value
            mock_client.images.get.return_value = "image_object"

            result = docker_backend._image_exists("test:image")
            assert result is True

            # Check that docker.images.get was called with correct image name
            mock_client.images.get.assert_called_once_with("test:image")

    def test_image_exists_false(self, docker_backend):
        """Test _image_exists when image doesn't exist."""
        with patch("docker.from_env") as mock_docker:
            mock_client = mock_docker.return_value
            mock_client.images.get.side_effect = docker.errors.ImageNotFound(
                "No such image"
            )

            result = docker_backend._image_exists("nonexistent:image")
            assert result is False

            # Check that docker.images.get was called with correct image name
            mock_client.images.get.assert_called_once_with("nonexistent:image")

    def test_get_run_command_simple(self, docker_backend):
        """Test _get_run_command with simple parameters."""
        result = docker_backend._get_run_command(
            executable="/usr/bin/test", mpiexec="", cpu=1
        )

        assert "cd /app/run_id" in result
        assert "ls -la" in result
        assert "/usr/bin/test" in result
        assert "mpiexec" not in result

    def test_get_run_command_with_mpi(self, docker_backend):
        """Test _get_run_command with MPI parameters."""
        result = docker_backend._get_run_command(
            executable="/usr/bin/test", mpiexec="mpiexec", cpu=4
        )

        assert "cd /app/run_id" in result
        assert "mpiexec --allow-run-as-root -n 4 /usr/bin/test" in result

    def test_prepare_volumes(self, docker_backend, model_run, tmp_path):
        """Test _prepare_volumes method."""
        # Set up the model run output directory
        model_run.output_dir = tmp_path

        volumes = docker_backend._prepare_volumes(
            model_run, additional_volumes=["extra:/extra:ro"]
        )

        expected_run_dir = tmp_path / model_run.run_id
        assert f"{expected_run_dir.absolute()}:/app/run_id:Z" in volumes
        assert "extra:/extra:ro" in volumes
        assert len(volumes) == 2

    def test_prepare_volumes_no_additional(self, docker_backend, model_run, tmp_path):
        """Test _prepare_volumes with no additional volumes."""
        model_run.output_dir = tmp_path

        volumes = docker_backend._prepare_volumes(model_run, None)

        expected_run_dir = tmp_path / model_run.run_id
        assert f"{expected_run_dir.absolute()}:/app/run_id:Z" in volumes
        assert len(volumes) == 1


class TestDockerBackendMocked:
    """Tests for Docker backend with mocked Docker calls."""

    def test_run_container_success(self, docker_backend):
        """Test _run_container with successful execution."""
        with patch("docker.from_env") as mock_docker:
            mock_client = mock_docker.return_value
            mock_client.containers.run.return_value = "container_output"

            result = docker_backend._run_container(
                image_name="test:image",
                run_command="echo test",
                volume_mounts=["/host:/container"],
                env_vars={"TEST": "value"},
            )

            assert result is True
            mock_client.containers.run.assert_called_once()

            # Check that the container was run with correct parameters
            call_kwargs = mock_client.containers.run.call_args[1]
            assert call_kwargs["image"] == "test:image"
            assert call_kwargs["command"] == ["bash", "-c", "echo test"]
            assert call_kwargs["environment"] == {"TEST": "value"}
            assert call_kwargs["remove"] is True

    def test_run_container_failure(self, docker_backend):
        """Test _run_container with container error."""
        with patch("docker.from_env") as mock_docker:
            mock_client = mock_docker.return_value
            from unittest.mock import Mock

            mock_container = Mock()
            mock_client.containers.run.side_effect = docker.errors.ContainerError(
                mock_container, 1, "echo test", "test:image", "Container failed"
            )

            result = docker_backend._run_container(
                image_name="test:image",
                run_command="echo test",
                volume_mounts=[],
                env_vars={},
            )

            assert result is False

    def test_run_container_image_not_found(self, docker_backend):
        """Test _run_container with image not found."""
        with patch("docker.from_env") as mock_docker:
            mock_client = mock_docker.return_value
            mock_client.containers.run.side_effect = docker.errors.ImageNotFound(
                "No such image"
            )

            result = docker_backend._run_container(
                image_name="nonexistent:image",
                run_command="echo test",
                volume_mounts=[],
                env_vars={},
            )

            assert result is False

    def test_run_container_api_error(self, docker_backend):
        """Test _run_container with Docker API error."""
        with patch("docker.from_env") as mock_docker:
            mock_client = mock_docker.return_value
            mock_client.containers.run.side_effect = docker.errors.APIError("API error")

            result = docker_backend._run_container(
                image_name="test:image",
                run_command="echo test",
                volume_mounts=[],
                env_vars={},
            )

            assert result is False

    def test_run_container_exception(self, docker_backend):
        """Test _run_container with generic exception."""
        with patch("docker.from_env") as mock_docker:
            mock_client = mock_docker.return_value
            mock_client.containers.run.side_effect = Exception("Docker not available")

            result = docker_backend._run_container(
                image_name="test:image",
                run_command="echo test",
                volume_mounts=[],
                env_vars={},
            )

            assert result is False

    def test_run_end_to_end_success(self, model_run, docker_backend, tmp_path):
        """Test complete run method with mocked Docker calls."""
        # Create DockerConfig
        config = DockerConfig(image="test:image", executable="echo", cpu=1)

        # Mock the generate method
        with patch(
            "rompy.model.ModelRun.generate",
            return_value=str(tmp_path / model_run.run_id),
        ):
            # Mock all Docker operations
            with patch.object(
                docker_backend, "_prepare_image", return_value="test:image"
            ):
                with patch.object(docker_backend, "_run_container", return_value=True):
                    result = docker_backend.run(model_run, config)

                    assert result is True

    def test_run_end_to_end_image_failure(self, model_run, docker_backend, tmp_path):
        """Test complete run method with image preparation failure."""
        # Create a build context with dockerfile
        context_dir = tmp_path / "build_context"
        context_dir.mkdir()
        dockerfile = context_dir / "Dockerfile"
        dockerfile.write_text("FROM ubuntu:20.04\n")

        # Create DockerConfig
        config = DockerConfig(
            dockerfile=Path("Dockerfile"),  # Relative to build context
            build_context=context_dir,
            executable="echo",
            cpu=1,
        )

        with patch(
            "rompy.model.ModelRun.generate",
            return_value=str(tmp_path / model_run.run_id),
        ):
            with patch.object(docker_backend, "_prepare_image", return_value=None):
                result = docker_backend.run(model_run, config)

                assert result is False

    def test_run_end_to_end_container_failure(
        self, model_run, docker_backend, tmp_path
    ):
        """Test complete run method with container execution failure."""
        # Create DockerConfig
        config = DockerConfig(image="test:image", executable="echo", cpu=1)

        with patch(
            "rompy.model.ModelRun.generate",
            return_value=str(tmp_path / model_run.run_id),
        ):
            with patch.object(
                docker_backend, "_prepare_image", return_value="test:image"
            ):
                with patch.object(docker_backend, "_run_container", return_value=False):
                    result = docker_backend.run(model_run, config)

                    assert result is False
