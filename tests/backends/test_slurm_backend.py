"""
Unit tests for the SLURM backend configuration and execution.

Tests verify that the SLURM backend configuration class works correctly,
provides proper validation, and integrates with the SLURM execution backend.
"""

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch, mock_open
import tempfile
import os
import pytest
from pydantic import ValidationError

from rompy.backends import SlurmConfig


class TestSlurmConfig:
    """Test the SlurmConfig class."""

    def test_default_values(self):
        """Test default values for SlurmConfig."""
        config = SlurmConfig(
            queue="general",  # Required field
        )

        assert config.timeout == 3600
        assert config.env_vars == {}
        assert config.working_dir is None
        assert config.queue == "general"
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
            config = SlurmConfig(queue="test", time_limit=time_limit)
            assert config.time_limit == time_limit

        # Invalid time limits (format-based validation)
        invalid_time_limits = [
            "00:00",      # Missing seconds
            "invalid",    # Not matching format
            "1:1:1",      # Not in HH:MM:SS format (only 1 digit for each part)
            "25-00-00",   # Wrong separator
            "12345:00:00", # Too many digits for hours (5 digits instead of max 4)
            "23:5",       # Missing seconds part
            ":23:59",     # Missing hours
            "23::59",     # Missing minutes
        ]

        for time_limit in invalid_time_limits:
            with pytest.raises(ValidationError):
                SlurmConfig(queue="test", time_limit=time_limit)

    def test_additional_options_validation(self):
        """Test additional options validation."""
        # Valid additional options
        config = SlurmConfig(
            queue="test",
            additional_options=["--gres=gpu:1", "--exclusive", "--mem-per-cpu=2048"]
        )
        assert config.additional_options == ["--gres=gpu:1", "--exclusive", "--mem-per-cpu=2048"]

        # Empty list should be valid
        config = SlurmConfig(queue="test", additional_options=[])
        assert config.additional_options == []

    def test_get_backend_class(self):
        """Test that get_backend_class returns the correct class."""
        config = SlurmConfig(queue="test")
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

    def test_required_queue_field(self):
        """Test that queue field is required."""
        # Should fail without queue
        with pytest.raises(ValidationError, match="Field required"):
            SlurmConfig()

        # Should work with queue
        config = SlurmConfig(queue="general")
        assert config.queue == "general"

    def test_field_boundaries(self):
        """Test field boundary values."""
        # Test minimum values
        config = SlurmConfig(
            queue="test",
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
            nodes=100,  # Max nodes
            cpus_per_task=128,  # Max cpus per task
        )
        assert config.nodes == 100
        assert config.cpus_per_task == 128

        # Test out of bounds
        with pytest.raises(ValidationError):
            SlurmConfig(queue="test", nodes=0)  # Min nodes is 1

        with pytest.raises(ValidationError):
            SlurmConfig(queue="test", nodes=101)  # Max nodes is 100

        with pytest.raises(ValidationError):
            SlurmConfig(queue="test", cpus_per_task=0)  # Min cpus_per_task is 1

        with pytest.raises(ValidationError):
            SlurmConfig(queue="test", cpus_per_task=129)  # Max cpus_per_task is 128


class TestSlurmRunBackend:
    """Test the SlurmRunBackend class."""

    @pytest.fixture
    def mock_model_run(self):
        """Create a mock ModelRun instance."""
        model_run = MagicMock()
        model_run.run_id = "test_run_123"
        model_run.output_dir = Path("/tmp/test_output")

        # Create a temporary directory for staging
        import tempfile

        temp_dir = tempfile.mkdtemp()
        model_run.generate.return_value = temp_dir
        model_run.config.run.return_value = True
        model_run.model_dump.return_value = {"test": "data"}  # Mock for serialization
        return model_run

    @pytest.fixture
    def basic_config(self):
        """Create a basic SlurmConfig."""
        return SlurmConfig(
            queue="general",
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
            script_path = backend._create_job_script(mock_model_run, basic_config, staging_dir)
            
            # Verify the file was created
            assert os.path.exists(script_path)
            
            # Read and check the contents
            with open(script_path, 'r') as f:
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
            script_path = backend._create_job_script(mock_model_run, config, staging_dir)
            
            with open(script_path, 'r') as f:
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

    def test_submit_job(self, basic_config):
        """Test the _submit_job method."""
        from rompy.run.slurm import SlurmRunBackend
        
        backend = SlurmRunBackend()
        
        # Create a simple job script
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
            f.write("#!/bin/bash\n#SBATCH --job-name=test\n")
            script_path = f.name
        
        try:
            # Mock subprocess.run to return a successful job submission
            with patch("subprocess.run") as mock_run:
                mock_run.return_value.stdout = "Submitted batch job 12345"
                mock_run.return_value.stderr = ""
                mock_run.return_value.returncode = 0
                
                job_id = backend._submit_job(script_path)
                
                assert job_id == "12345"
                mock_run.assert_called_once()
                
        finally:
            # Clean up
            if os.path.exists(script_path):
                os.remove(script_path)

    def test_submit_job_failure(self, basic_config):
        """Test the _submit_job method with failure."""
        from rompy.run.slurm import SlurmRunBackend
        
        backend = SlurmRunBackend()
        
        # Create a simple job script
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
            f.write("#!/bin/bash\n#SBATCH --job-name=test\n")
            script_path = f.name
        
        try:
            # Mock subprocess.run to return a failure
            with patch("subprocess.run") as mock_run:
                mock_run.side_effect = Exception("Submission failed")
                
                job_id = backend._submit_job(script_path)
                
                assert job_id is None
                mock_run.assert_called_once()
                
        finally:
            # Clean up
            if os.path.exists(script_path):
                os.remove(script_path)

    def test_wait_for_completion_completed(self, basic_config):
        """Test _wait_for_completion method for completed job."""
        from rompy.run.slurm import SlurmRunBackend
        
        backend = SlurmRunBackend()
        
        # Mock subprocess.run for squeue to return completed state
        with patch("subprocess.run") as mock_run:
            # First call returns running, second returns completed
            mock_run.side_effect = [
                # Running
                MagicMock(
                    stdout="R\n",
                    stderr="",
                    returncode=0
                ),
                # Completed 
                MagicMock(
                    stdout="CD\n",
                    stderr="",
                    returncode=0
                )
            ]
            
            result = backend._wait_for_completion("12345", basic_config)
            
            assert result is True
            assert mock_run.call_count == 2

    def test_wait_for_completion_failed(self, basic_config):
        """Test _wait_for_completion method for failed job."""
        from rompy.run.slurm import SlurmRunBackend
        
        backend = SlurmRunBackend()
        
        # Mock subprocess.run for squeue to return failed state
        with patch("subprocess.run") as mock_run:
            mock_result = MagicMock(stdout="F\n", stderr="", returncode=0)
            mock_run.return_value = mock_result
            
            result = backend._wait_for_completion("12345", basic_config)
            
            assert result is False

    def test_wait_for_completion_timeout(self):
        """Test _wait_for_completion method with timeout."""
        from rompy.run.slurm import SlurmRunBackend
        import time
        from unittest.mock import ANY
        
        config = SlurmConfig(
            queue="test",
            timeout=60,  # Minimum valid timeout value
            nodes=1,
            ntasks=1,
            cpus_per_task=1,
            time_limit="01:00:00",
        )
        
        backend = SlurmRunBackend()
        
        # Use a more advanced approach with time mocking
        initial_time = time.time()
        def time_side_effect():
            # Return an increasing time value to simulate timeout
            return initial_time + 120  # More than 60s timeout
        
        with patch("subprocess.run") as mock_run:
            with patch("time.time", side_effect=time_side_effect):
                # Return running state to avoid early exit due to job completion
                mock_result = MagicMock(stdout="R\n", stderr="", returncode=0)
                mock_run.return_value = mock_result
                
                result = backend._wait_for_completion("12345", config)
                
                # Should return False due to timeout
                assert result is False
                
                # Verify that scancel was called during timeout handling
                mock_run.assert_any_call(['scancel', '12345'], check=True, capture_output=True)

    def test_run_method_success(self, mock_model_run, basic_config):
        """Test the full run method with success."""
        from rompy.run.slurm import SlurmRunBackend
        
        backend = SlurmRunBackend()
        
        with TemporaryDirectory() as staging_dir:
            # Mock the internal methods
            with patch.object(backend, '_create_job_script') as mock_create_script, \
                 patch.object(backend, '_submit_job') as mock_submit, \
                 patch.object(backend, '_wait_for_completion') as mock_wait:
                
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
            with patch.object(backend, '_create_job_script') as mock_create_script, \
                 patch.object(backend, '_submit_job') as mock_submit:
                
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