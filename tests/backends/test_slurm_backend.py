"""
Unit tests for the SLURM backend configuration and execution.

Tests verify that the SLURM backend configuration class works correctly,
provides proper validation, and integrates with the SLURM execution backend.
"""

import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch
import os
import tempfile
import pytest
from pydantic import ValidationError

from rompy.backends import SlurmConfig


def is_slurm_available():
    """Check if SLURM is available on the system."""
    try:
        result = subprocess.run(
            ["which", "sbatch"], capture_output=True, text=True, timeout=5
        )
        return result.returncode == 0 and bool(result.stdout.strip())
    except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
        return False


# Skip tests that require SLURM if it's not available
requires_slurm = pytest.mark.skipif(
    not is_slurm_available(), reason="SLURM is not available on this system"
)


class TestSlurmConfig:
    """Test the SlurmConfig class."""

    def test_default_values(self):
        """Test default values for SlurmConfig."""
        config = SlurmConfig(
            queue="general",  # Required field
            command="python run_model.py",  # Required field
        )

        assert config.timeout == 3600
        assert config.env_vars == {}
        assert config.working_dir is None
        assert config.queue == "general"
        assert config.command == "python run_model.py"
        assert config.nodes == 1
        assert config.ntasks == 1
        assert config.cpus_per_task == 1
        assert config.time_limit == "1:00:00"
        assert config.account is None
        assert config.qos is None
        assert config.reservation is None
        assert config.output_file is None
        assert config.error_file is None
        assert config.job_name is None
        assert config.mail_type is None
        assert config.mail_user is None
        assert config.additional_options == []

    def test_custom_values(self):
        """Test setting custom values."""
        with TemporaryDirectory() as tmp_dir:
            config = SlurmConfig(
                queue="compute",
                command="python run_model.py --param value",
                nodes=2,
                ntasks=4,
                cpus_per_task=8,
                time_limit="24:00:00",
                account="myproject",
                qos="priority",
                reservation="special_reservation",
                output_file="slurm-%j.out",
                error_file="slurm-%j.err",
                job_name="test_job",
                mail_type="END",
                mail_user="test@example.com",
                additional_options=["--gres=gpu:1", "--exclusive"],
                timeout=7200,
                env_vars={"OMP_NUM_THREADS": "8"},
                working_dir=Path(tmp_dir),
            )

            assert config.queue == "compute"
            assert config.nodes == 2
            assert config.ntasks == 4
            assert config.cpus_per_task == 8
            assert config.time_limit == "24:00:00"
            assert config.account == "myproject"
            assert config.qos == "priority"
            assert config.reservation == "special_reservation"
            assert config.output_file == "slurm-%j.out"
            assert config.error_file == "slurm-%j.err"
            assert config.job_name == "test_job"
            assert config.mail_type == "END"
            assert config.mail_user == "test@example.com"
            assert config.additional_options == ["--gres=gpu:1", "--exclusive"]
            assert config.timeout == 7200
            assert config.env_vars == {"OMP_NUM_THREADS": "8"}
            assert config.working_dir == Path(tmp_dir)

    def test_time_limit_validation(self):
        """Test time limit validation."""
        # Valid time limits
        valid_time_limits = [
            "01:00:00",
            "00:30:00",
            "23:59:59",
            "100:00:00",  # Allow longer times for long jobs
        ]

        for time_limit in valid_time_limits:
            config = SlurmConfig(
                queue="test", command="python run_model.py", time_limit=time_limit
            )
            assert config.time_limit == time_limit

        # Invalid time limits (format-based validation)
        invalid_time_limits = [
            "00:00",  # Missing seconds
            "invalid",  # Not matching format
            "1:1:1",  # Not in HH:MM:SS format (only 1 digit for each part)
            "25-00-00",  # Wrong separator
            "12345:00:00",  # Too many digits for hours (5 digits instead of max 4)
            "23:5",  # Missing seconds part
            ":23:59",  # Missing hours
            "23::59",  # Missing minutes
        ]

        for time_limit in invalid_time_limits:
            with pytest.raises(ValidationError):
                SlurmConfig(
                    queue="test", command="python run_model.py", time_limit=time_limit
                )

    def test_additional_options_validation(self):
        """Test additional options validation."""
        # Valid additional options
        config = SlurmConfig(
            queue="test",
            command="python run_model.py",
            additional_options=["--gres=gpu:1", "--exclusive", "--mem-per-cpu=2048"],
        )
        assert config.additional_options == [
            "--gres=gpu:1",
            "--exclusive",
            "--mem-per-cpu=2048",
        ]

        # Empty list should be valid
        config = SlurmConfig(
            queue="test", command="python run_model.py", additional_options=[]
        )
        assert config.additional_options == []

    def test_get_backend_class(self):
        """Test that get_backend_class returns the correct class."""
        config = SlurmConfig(queue="test", command="python run_model.py")
        backend_class = config.get_backend_class()

        # Should return SlurmRunBackend class
        assert backend_class.__name__ == "SlurmRunBackend"

    def test_config_examples(self):
        """Test that the schema examples are valid."""
        schema = SlurmConfig.model_json_schema()
        examples = schema.get("examples", [])

        for example in examples:
            # Should be able to create config from example
            config = SlurmConfig(**example)
            assert isinstance(config, SlurmConfig)

    def test_queue_field_is_optional(self):
        """Test that queue field is optional."""
        # Should work without queue (None)
        config = SlurmConfig(command="python run_model.py")
        assert config.queue is None

        # Should work with queue
        config = SlurmConfig(queue="general", command="python run_model.py")
        assert config.queue == "general"

    def test_field_boundaries(self):
        """Test field boundary values."""
        # Test minimum values
        config = SlurmConfig(
            queue="test",
            command="python run_model.py",
            nodes=1,
            ntasks=1,
            cpus_per_task=1,
        )
        assert config.nodes == 1
        assert config.ntasks == 1
        assert config.cpus_per_task == 1

        # Test maximum values
        config = SlurmConfig(
            queue="test",
            command="python run_model.py",
            nodes=100,  # Max nodes
            cpus_per_task=128,  # Max cpus per task
        )
        assert config.nodes == 100
        assert config.cpus_per_task == 128

        # Test out of bounds
        with pytest.raises(ValidationError):
            SlurmConfig(
                queue="test", command="python run_model.py", nodes=0
            )  # Min nodes is 1

        with pytest.raises(ValidationError):
            SlurmConfig(
                queue="test", command="python run_model.py", nodes=101
            )  # Max nodes is 100

        with pytest.raises(ValidationError):
            SlurmConfig(
                queue="test", command="python run_model.py", cpus_per_task=0
            )  # Min cpus_per_task is 1

        with pytest.raises(ValidationError):
            SlurmConfig(
                queue="test", command="python run_model.py", cpus_per_task=129
            )  # Max cpus_per_task is 128

    def test_command_field(self):
        """Test the command field validation and functionality."""
        # Test with a custom command
        config = SlurmConfig(
            queue="test",
            command="python my_script.py --param value",
        )
        assert config.command == "python my_script.py --param value"

        # Test with no command provided - this should now raise an error since command is required
        with pytest.raises(ValidationError):
            SlurmConfig(queue="test")

        # Test with empty command - this should now raise an error since command is required
        with pytest.raises(ValidationError):
            SlurmConfig(queue="test", command="")


class TestSlurmRunBackend:
    """Test the SlurmRunBackend class."""

    @pytest.fixture
    def mock_model_run(self):
        """Create a mock ModelRun instance."""
        model_run = MagicMock()
        model_run.run_id = "test_run_123"
        model_run.output_dir = Path("/tmp/test_output")

        # Will be set to a temporary directory by individual tests as needed
        # This avoids creating directories that aren't cleaned up
        model_run.config.run.return_value = True
        model_run.model_dump.return_value = {"test": "data"}  # Mock for serialization
        return model_run

    @pytest.fixture
    def basic_config(self):
        """Create a basic SlurmConfig."""
        return SlurmConfig(
            queue="general",
            command="python run_model.py",
            timeout=3600,
            nodes=1,
            ntasks=1,
            cpus_per_task=2,
            time_limit="01:00:00",
        )

    def test_create_job_script(self, mock_model_run, basic_config):
        """Test the _create_job_script method."""
        from rompy.run.slurm import SlurmRunBackend

        backend = SlurmRunBackend()

        with TemporaryDirectory() as staging_dir:
            # Create the job script
            script_path = backend._create_job_script(
                mock_model_run, basic_config, staging_dir
            )

            # Verify the file was created
            assert os.path.exists(script_path)

            # Read and check the contents
            with open(script_path, "r") as f:
                content = f.read()

            # Check for SLURM directives
            assert "#!/bin/bash" in content
            assert "#SBATCH --partition=general" in content
            assert "#SBATCH --nodes=1" in content
            assert "#SBATCH --ntasks=1" in content
            assert "#SBATCH --cpus-per-task=2" in content
            assert "#SBATCH --time=01:00:00" in content

            # Clean up
            if os.path.exists(script_path):
                os.remove(script_path)

    def test_create_job_script_with_all_options(self, mock_model_run):
        """Test the _create_job_script method with all options."""
        from rompy.run.slurm import SlurmRunBackend

        config = SlurmConfig(
            queue="priority",
            nodes=2,
            ntasks=4,
            cpus_per_task=8,
            time_limit="24:00:00",
            command="echo 'Test'",
            account="myproject",
            qos="high",
            reservation="special",
            output_file="output_%j.txt",
            error_file="error_%j.txt",
            job_name="test_job",
            mail_type="BEGIN,END,FAIL",
            mail_user="test@example.com",
            additional_options=["--gres=gpu:1", "--exclusive"],
            timeout=86400,
            env_vars={"OMP_NUM_THREADS": "8", "MY_VAR": "value"},
        )

        backend = SlurmRunBackend()

        with TemporaryDirectory() as staging_dir:
            script_path = backend._create_job_script(
                mock_model_run, config, staging_dir
            )

            with open(script_path, "r") as f:
                content = f.read()

            # Check for all SBATCH directives
            assert "#SBATCH --partition=priority" in content
            assert "#SBATCH --nodes=2" in content
            assert "#SBATCH --ntasks=4" in content
            assert "#SBATCH --cpus-per-task=8" in content
            assert "#SBATCH --time=24:00:00" in content
            assert "#SBATCH --account=myproject" in content
            assert "#SBATCH --qos=high" in content
            assert "#SBATCH --reservation=special" in content
            assert "#SBATCH --output=output_%j.txt" in content
            assert "#SBATCH --error=error_%j.txt" in content
            assert "#SBATCH --job-name=test_job" in content
            assert "#SBATCH --mail-type=BEGIN,END,FAIL" in content
            assert "#SBATCH --mail-user=test@example.com" in content
            assert "#SBATCH --gres=gpu:1" in content
            assert "#SBATCH --exclusive" in content

            # Check for environment variables
            assert "export OMP_NUM_THREADS=8" in content
            assert "export MY_VAR=value" in content

            # Clean up
            if os.path.exists(script_path):
                os.remove(script_path)

    def test_create_job_script_with_command(self, mock_model_run):
        """Test the _create_job_script method with command."""
        from rompy.run.slurm import SlurmRunBackend

        # Create a config with a command
        config = SlurmConfig(
            queue="general",
            command="python my_script.py --param value",
            nodes=1,
            ntasks=1,
            cpus_per_task=1,
            time_limit="01:00:00",
        )

        backend = SlurmRunBackend()

        with TemporaryDirectory() as staging_dir:
            script_path = backend._create_job_script(
                mock_model_run, config, staging_dir
            )

            with open(script_path, "r") as f:
                content = f.read()

            # Check that the command is in the script
            assert "python my_script.py --param value" in content
            # Check that it's properly marked as command execution
            assert "# Execute command in the workspace" in content
            # Make sure the old model execution is not present
            assert "# Execute model using model_run.config.run() method" not in content

            # Clean up
            if os.path.exists(script_path):
                os.remove(script_path)

    def test_submit_job(self, basic_config):
        """Test the _submit_job method."""
        from rompy.run.slurm import SlurmRunBackend

        backend = SlurmRunBackend()

        # Create a simple job script
        with tempfile.NamedTemporaryFile(mode="w", suffix=".sh", delete=False) as f:
            f.write("#!/bin/bash\n#SBATCH --job-name=test\n")
            script_path = f.name

        try:
            # Mock subprocess.run to return a successful job submission
            # We need to mock multiple subprocess calls: which sbatch, scontrol, and sbatch
            with patch("subprocess.run") as mock_run:
                # Configure the side effect to simulate the sequence of calls in _submit_job
                mock_run.side_effect = [
                    # First call: which sbatch - return success
                    MagicMock(returncode=0, stdout="/usr/bin/sbatch"),
                    # Second call: scontrol --help - return success
                    MagicMock(returncode=0, stdout="scontrol help text"),
                    # Third call: sbatch command - return success
                    MagicMock(
                        returncode=0, stdout="Submitted batch job 12345", stderr=""
                    ),
                ]

                job_id = backend._submit_job(script_path)

                assert job_id == "12345"
                # Check that subprocess.run was called exactly 3 times
                assert mock_run.call_count == 3

        finally:
            # Clean up
            if os.path.exists(script_path):
                os.remove(script_path)

    def test_submit_job_failure(self, basic_config):
        """Test the _submit_job method with failure."""
        from rompy.run.slurm import SlurmRunBackend

        backend = SlurmRunBackend()

        # Create a simple job script
        with tempfile.NamedTemporaryFile(mode="w", suffix=".sh", delete=False) as f:
            f.write("#!/bin/bash\n#SBATCH --job-name=test\n")
            script_path = f.name

        try:
            # Mock subprocess.run to return a failure during sbatch command
            with patch("subprocess.run") as mock_run:
                # Mock the sequence of calls but make sbatch fail
                mock_run.side_effect = [
                    # First call: which sbatch - return success
                    MagicMock(returncode=0, stdout="/usr/bin/sbatch"),
                    # Second call: scontrol --help - return success
                    MagicMock(returncode=0, stdout="scontrol help text"),
                    # Third call: sbatch command - return failure
                    subprocess.CalledProcessError(
                        1, "sbatch", stderr="SLURM submission failed"
                    ),
                ]

                job_id = backend._submit_job(script_path)

                assert job_id is None
                assert mock_run.call_count == 3  # All three calls attempted

        finally:
            # Clean up
            if os.path.exists(script_path):
                os.remove(script_path)

    def test_wait_for_completion_completed(self, basic_config):
        """Test _wait_for_completion method for completed job."""
        from rompy.run.slurm import SlurmRunBackend

        backend = SlurmRunBackend()

        # Mock subprocess.run for scontrol to return completed state
        with patch("subprocess.run") as mock_run:
            # First call returns running, second returns completed
            mock_run.side_effect = [
                # Running state from scontrol
                MagicMock(
                    stdout="JobState=RUNNING\nOtherInfo=...", stderr="", returncode=0
                ),
                # Completed state from scontrol
                MagicMock(
                    stdout="JobState=COMPLETED\nOtherInfo=...", stderr="", returncode=0
                ),
            ]

            result = backend._wait_for_completion("12345", basic_config)

            assert result is True
            assert mock_run.call_count == 2

    def test_wait_for_completion_failed(self, basic_config):
        """Test _wait_for_completion method for failed job."""
        from rompy.run.slurm import SlurmRunBackend

        backend = SlurmRunBackend()

        # Mock subprocess.run for scontrol to return failed state
        with patch("subprocess.run") as mock_run:
            mock_result = MagicMock(
                stdout="JobState=FAILED\nOtherInfo=...", stderr="", returncode=0
            )
            mock_run.return_value = mock_result

            result = backend._wait_for_completion("12345", basic_config)

            assert result is False

    def test_wait_for_completion_timeout(self):
        """Test _wait_for_completion method with timeout."""
        from rompy.run.slurm import SlurmRunBackend
        import time

        config = SlurmConfig(
            queue="test",
            command="python run_model.py",  # Added required command field
            timeout=60,  # Minimum valid timeout value
            nodes=1,
            ntasks=1,
            cpus_per_task=1,
            time_limit="01:00:00",
        )

        backend = SlurmRunBackend()

        # Track the call count to simulate time progression with each call
        call_count = 0
        initial_time = time.time()

        def time_side_effect():
            # Simulate time progressing 10 seconds per call to trigger timeout faster
            nonlocal call_count
            call_count += 1
            return initial_time + (call_count * 10)  # Increment time by 10s per call

        with patch("subprocess.run") as mock_run:
            with patch("time.time", side_effect=time_side_effect):
                with patch("time.sleep"):  # Mock time.sleep to avoid actual sleeping
                    # Mock scontrol to return RUNNING state to simulate a job that keeps running
                    def scontrol_side_effect(*args, **kwargs):
                        return MagicMock(
                            stdout="JobState=RUNNING\nOtherInfo=...",
                            stderr="",
                            returncode=0,
                        )

                    mock_run.side_effect = scontrol_side_effect

                    result = backend._wait_for_completion("12345", config)

                    # Should return False due to timeout
                    assert result is False

                    # In the original implementation, the timeout was handled without scancel
                    # so we don't expect scancel to be called

    def test_run_method_success(self, mock_model_run, basic_config):
        """Test the full run method with success."""
        from rompy.run.slurm import SlurmRunBackend

        backend = SlurmRunBackend()

        with TemporaryDirectory() as staging_dir:
            # Mock the internal methods
            with (
                patch.object(backend, "_create_job_script") as mock_create_script,
                patch.object(backend, "_submit_job") as mock_submit,
                patch.object(backend, "_wait_for_completion") as mock_wait,
            ):

                # Mock the methods to return expected values
                mock_create_script.return_value = "/tmp/job_script.sh"
                mock_submit.return_value = "12345"
                mock_wait.return_value = True  # Job completed successfully

                # Set up the mock model run to return the staging directory
                mock_model_run.generate.return_value = staging_dir

                result = backend.run(mock_model_run, basic_config)

                assert result is True
                mock_create_script.assert_called_once()
                mock_submit.assert_called_once()
                mock_wait.assert_called_once_with("12345", basic_config)

    def test_run_method_job_submit_failure(self, mock_model_run, basic_config):
        """Test the run method when job submission fails."""
        from rompy.run.slurm import SlurmRunBackend

        backend = SlurmRunBackend()

        with TemporaryDirectory() as staging_dir:
            # Mock the internal methods
            with (
                patch.object(backend, "_create_job_script") as mock_create_script,
                patch.object(backend, "_submit_job") as mock_submit,
            ):

                # Mock the methods
                mock_create_script.return_value = "/tmp/job_script.sh"
                mock_submit.return_value = None  # Submission failed

                # Set up the mock model run
                mock_model_run.generate.return_value = staging_dir

                result = backend.run(mock_model_run, basic_config)

                assert result is False
                mock_create_script.assert_called_once()
                mock_submit.assert_called_once()

    def test_run_method_generation_failure(self, mock_model_run, basic_config):
        """Test the run method when model generation fails."""
        from rompy.run.slurm import SlurmRunBackend

        backend = SlurmRunBackend()

        # Configure mock to raise an exception during generation
        mock_model_run.generate.side_effect = Exception("Generation failed")

        result = backend.run(mock_model_run, basic_config)

        assert result is False
