#!/usr/bin/env python3
"""
Test Backend Configurations with Basic ModelRun

This script demonstrates how to use the basic ModelRun configuration
with different backend configurations.
"""

import logging
import tempfile
from datetime import datetime
from pathlib import Path

from rompy.backends import DockerConfig, LocalConfig, SlurmConfig
from rompy.core.time import TimeRange
from rompy.model import ModelRun


# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def create_basic_model_run():
    """
    Create a basic model run configuration for testing backends.
    """
    temp_dir = Path(tempfile.mkdtemp(prefix="rompy_test_"))
    
    model_run = ModelRun(
        run_id="test_backend_run",
        period=TimeRange(
            start=datetime(2023, 1, 1),
            end=datetime(2023, 1, 2),
            interval="1H",
        ),
        output_dir=temp_dir,
        delete_existing=True,
    )

    return model_run


def test_local_backend():
    """Test the local backend with basic configuration."""
    logger.info("Testing Local Backend Configuration")
    logger.info("-" * 40)
    
    model = create_basic_model_run()
    
    # Create local backend configuration
    config = LocalConfig(
        timeout=1800,  # 30 minutes
        command="echo 'Running model on local backend' && pwd && date",
        env_vars={
            "MODEL_TYPE": "test",
            "ENVIRONMENT": "local"
        },
        shell=True,
        capture_output=True
    )
    
    logger.info(f"LocalConfig: {config}")
    
    # Note: In a real environment, you would run:
    # success = model.run(backend=config)
    # For this example, we'll just validate the configuration works
    logger.info("Local backend configuration validated successfully")
    logger.info(f"Working directory: {model.output_dir}")

def test_docker_backend():
    """Test the Docker backend with basic configuration."""
    logger.info("Testing Docker Backend Configuration")
    logger.info("-" * 40)
    
    model = create_basic_model_run()
    
    # Create Docker backend configuration
    config = DockerConfig(
        image="python:3.9-slim",
        timeout=1800,
        cpu=2,
        memory="1g",
        executable="python -c \"print('Running model in Docker'); import os; print(f'Working in: {os.getcwd()}')\"",
        volumes=[f"{model.output_dir}:/app/work:rw"],
        env_vars={
            "MODEL_TYPE": "test",
            "ENVIRONMENT": "docker",
            "PYTHONUNBUFFERED": "1"
        }
    )
    
    logger.info(f"DockerConfig: {config}")
    
    # Validate the configuration
    logger.info("Docker backend configuration validated successfully")
    logger.info(f"Working directory: {model.output_dir}")

def test_slurm_backend():
    """Test the SLURM backend with basic configuration."""
    logger.info("Testing SLURM Backend Configuration")
    logger.info("-" * 40)
    
    model = create_basic_model_run()
    
    # Create SLURM backend configuration
    config = SlurmConfig(
        queue="general",
        timeout=1800,
        nodes=1,
        ntasks=1,
        cpus_per_task=2,
        time_limit="00:30:00",
        job_name="test_backend_job",
        output_file=f"{model.output_dir}/slurm-%j.out",
        error_file=f"{model.output_dir}/slurm-%j.err",
        env_vars={
            "MODEL_TYPE": "test",
            "ENVIRONMENT": "slurm"
        },
        command="echo 'Running model on SLURM backend' && pwd && date && env | grep MODEL"
    )
    
    logger.info(f"SlurmConfig: {config}")
    
    # Validate the configuration
    logger.info("SLURM backend configuration validated successfully")
    logger.info(f"Working directory: {model.output_dir}")

def main():
    """Run all backend tests."""
    logger.info("Testing Backend Configurations with Basic ModelRun")
    logger.info("=" * 50)
    logger.info("This script demonstrates how to configure different backends")
    logger.info("for the same basic ModelRun configuration.")
    # Test all backends
    test_local_backend()
    test_docker_backend()
    test_slurm_backend()

    logger.info("=" * 50)
    logger.info("All backend configurations validated successfully!")
    logger.info("Next steps:")
    logger.info("1. Try running these configurations on actual backend systems")
    logger.info("2. Adjust resource requirements based on your needs")
    logger.info("3. Add more complex commands or model executables")
    logger.info("4. Use the YAML configuration files in examples/configs/")


if __name__ == "__main__":
    main()