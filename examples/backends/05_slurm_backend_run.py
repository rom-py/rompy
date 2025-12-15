#!/usr/bin/env python3
"""
ROMPY SLURM Backend Example

This example demonstrates how to use the SLURM backend to run models on HPC clusters.
The SLURM backend enables resource management and job scheduling for high-performance
computing environments.

Run this example:
    python 05_slurm_backend_run.py

Note: This example requires access to a SLURM-managed HPC cluster.
"""

import logging
import tempfile
from datetime import datetime
from pathlib import Path

from rompy.backends import SlurmConfig
from rompy.core.time import TimeRange
from rompy.model import ModelRun

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def example_slurm_basic():
    """
    Example 1: Basic SLURM execution

    This example demonstrates the simplest configuration for running a model
    on a SLURM cluster with minimal parameters.
    """
    logger.info("=" * 60)
    logger.info("Example 1: Basic SLURM Execution")
    logger.info("=" * 60)
    logger.info("This example demonstrates the simplest SLURM backend configuration.")
    logger.info("")

    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a basic model run
        model = ModelRun(
            run_id="slurm_basic_example",
            period=TimeRange(
                start=datetime(2023, 1, 1),
                end=datetime(2023, 1, 2),
                interval="1H",
            ),
            output_dir=Path(temp_dir),
            delete_existing=True,
        )

        # Basic SLURM configuration
        config = SlurmConfig(
            command="python run_model.py",  # Command to run in the workspace
            timeout=1800,  # Max execution time in seconds (30 minutes)
            output_file="slurm-%j.out",  # Output file pattern (job ID)
            error_file="slurm-%j.err",  # Error file pattern
            nodes=1,  # Number of nodes to allocate
            ntasks=1,  # Number of tasks (processes) to run
            cpus_per_task=2,  # Number of CPU cores per task
            time_limit="00:30:00",  # Time limit in HH:MM:SS format
        )

        logger.info(f"SlurmConfig created: {config}")
        logger.info("Running model with basic SLURM configuration...")

        try:
            # Submit the job to SLURM (in a real environment)
            success = model.run(backend=config)
            if success:
                logger.info("✅ SLURM job submitted successfully")
            else:
                logger.info(
                    "⚠️  SLURM job submission completed but may have failed (e.g., in test environment)"
                )
            logger.info(
                "Key concepts: SlurmConfig, queue, nodes, ntasks, cpus_per_task"
            )
            logger.info(
                "Note: In a real SLURM environment, this would submit the job for execution"
            )
        except Exception as e:
            logger.error(f"❌ SLURM model run failed: {e}")
            logger.info(
                "Note: This may fail in non-SLURM environments, which is expected"
            )


def example_slurm_advanced():
    """
    Example 2: Advanced SLURM execution with multiple parameters

    This example shows how to configure complex SLURM jobs with multiple
    resource allocations, environment variables, and custom options.
    """
    logger.info("=" * 60)
    logger.info("Example 2: Advanced SLURM Configuration")
    logger.info("=" * 60)
    logger.info("This example demonstrates advanced SLURM backend configuration.")
    logger.info("")

    with tempfile.TemporaryDirectory() as temp_dir:
        model = ModelRun(
            run_id="slurm_advanced_example",
            period=TimeRange(
                start=datetime(2023, 1, 1),
                end=datetime(2023, 1, 3),
                interval="1H",
            ),
            output_dir=Path(temp_dir),
            delete_existing=True,
        )

        # Advanced SLURM configuration with many parameters
        config = SlurmConfig(
            command="python run_model.py",  # Command to run in the workspace
            timeout=7200,  # 2 hours timeout
            nodes=2,  # 2 compute nodes
            ntasks=8,  # 8 tasks total
            cpus_per_task=4,  # 4 CPUs per task
            time_limit="02:00:00",  # 2 hours time limit
            output_file="slurm-%j.out",  # Output file pattern (job ID)
            error_file="slurm-%j.err",  # Error file pattern
            job_name="advanced_simulation",  # Name of the SLURM job
            mail_type="BEGIN,END,FAIL",  # Types of notifications
            mail_user="researcher@domain.com",  # Email for notifications
            additional_options=["--exclusive"],  # GPU resources
            env_vars={  # Environment variables
                "OMP_NUM_THREADS": "4",
                "MODEL_DEBUG": "true",
                "DATA_PATH": "/shared/data",
                "RESULTS_PATH": "/shared/results",
            },
        )

        logger.info(f"Advanced SlurmConfig created: {config}")
        logger.info("Running model with advanced SLURM configuration...")

        try:
            success = model.run(backend=config)
            if success:
                logger.info("✅ Advanced SLURM job submitted successfully")
            else:
                logger.info(
                    "⚠️  Advanced SLURM job submission completed but may have failed"
                )
        except Exception as e:
            logger.error(f"❌ Advanced SLURM configuration failed: {e}")
            logger.info(
                "Note: This may fail in non-SLURM environments, which is expected"
            )


def example_slurm_with_custom_command():
    """
    Example 3: SLURM execution with custom command

    This example shows how to run a custom command on the SLURM cluster,
    useful for executing different types of jobs or calling external binaries.
    """
    logger.info("=" * 60)
    logger.info("Example 3: SLURM with Custom Command")
    logger.info("=" * 60)
    logger.info("This example demonstrates running custom commands on SLURM.")
    logger.info("")

    with tempfile.TemporaryDirectory() as temp_dir:
        model = ModelRun(
            run_id="slurm_custom_command_example",
            period=TimeRange(
                start=datetime(2023, 1, 1),
                end=datetime(2023, 1, 2),
                interval="1H",
            ),
            output_dir=Path(temp_dir),
            delete_existing=True,
        )

        # SLURM configuration with a custom command
        config = SlurmConfig(
            timeout=3600,  # 1 hour timeout
            nodes=1,
            ntasks=1,
            cpus_per_task=2,
            time_limit="01:00:00",
            command="echo 'Running custom SLURM job' && date && pwd && ls -la",  # Custom command
            env_vars={"CUSTOM_VAR": "value"},
        )

        logger.info(f"SlurmConfig with custom command: {config}")
        logger.info("Running custom command on SLURM...")

        try:
            success = model.run(backend=config)
            if success:
                logger.info("✅ SLURM job with custom command submitted successfully")
            else:
                logger.info(
                    "⚠️  SLURM job with custom command completed but may have failed"
                )
            logger.info("Key concepts: command parameter, custom execution")
            logger.info(
                "Note: In a real SLURM environment, this would execute the custom command"
            )
        except Exception as e:
            logger.error(f"❌ SLURM custom command configuration failed: {e}")
            logger.info(
                "Note: This may fail in non-SLURM environments, which is expected"
            )


def example_slurm_from_dict():
    """
    Example 4: Creating SLURM configuration from dictionary

    This example shows how to create SLURM configurations from dictionaries,
    which is useful when loading from configuration files (YAML/JSON).
    """
    logger.info("=" * 60)
    logger.info("Example 4: SLURM Configuration from Dictionary")
    logger.info("=" * 60)
    logger.info("This example demonstrates creating SLURM configs from dictionaries.")
    logger.info("")

    # Simulate loading from YAML/JSON file
    slurm_config_data = {
        "queue": "compute",
        "command": "python run_model.py",
        "timeout": 7200,
        "nodes": 1,
        "ntasks": 4,
        "cpus_per_task": 2,
        "time_limit": "02:00:00",
        "account": "myproject",
        "env_vars": {
            "OMP_NUM_THREADS": "2",
            "MODEL_PRECISION": "double",
            "DATA_DIR": "/shared/data",
        },
        "job_name": "yaml_configured_job",
        "additional_options": ["--mem-per-cpu=2048"],
    }

    try:
        # Create configuration from dictionary
        config = SlurmConfig(**slurm_config_data)

        logger.info("✅ SLURM configuration created from dictionary:")
        logger.info(f"  Queue: {config.queue}")
        logger.info(f"  Nodes: {config.nodes}")
        logger.info(f"  Total CPU cores: {config.ntasks * config.cpus_per_task}")
        logger.info(f"  Time limit: {config.time_limit}")
        logger.info(f"  Environment variables: {len(config.env_vars)}")
        logger.info("Key concepts: dictionary unpacking, YAML/JSON compatibility")
        logger.info("Note: This is how configuration files are loaded in production")
    except Exception as e:
        logger.error(f"❌ SLURM dictionary configuration failed: {e}")


def example_slurm_validation():
    """
    Example 5: SLURM configuration validation

    This example demonstrates ROMPY's built-in validation for SLURM configurations.
    The Pydantic model catches configuration errors before runtime.
    """
    logger.info("=" * 60)
    logger.info("Example 5: SLURM Configuration Validation")
    logger.info("=" * 60)
    logger.info(
        "This example shows how ROMPY validates SLURM configurations automatically."
    )
    logger.info("")

    from pydantic import ValidationError

    # Valid SLURM configuration
    try:
        valid_config = SlurmConfig(
            queue="general",
            command="python run_model.py",
            timeout=3600,
            nodes=1,
            ntasks=1,
            cpus_per_task=2,
            time_limit="01:00:00",
            env_vars={"TEST_VAR": "value"},
        )
        logger.info("✅ Valid SlurmConfig created successfully")
    except Exception as e:
        logger.error(f"❌ Valid SLURM config validation failed unexpectedly: {e}")

    # Invalid time limit format
    logger.info("Testing invalid time limit format...")
    try:
        invalid_config = SlurmConfig(
            queue="general",
            command="python run_model.py",
            time_limit="25:00",  # Invalid format - missing seconds
        )
        logger.info("❌ This should not succeed")
    except ValidationError as e:
        logger.info(
            f"✅ Validation correctly caught time limit error: {e.errors()[0]['msg']}"
        )

    # Invalid number of nodes (too high)
    logger.info("Testing invalid number of nodes...")
    try:
        invalid_config = SlurmConfig(
            queue="general",
            command="python run_model.py",
            nodes=101,  # Max is 100
            time_limit="01:00:00",
        )
        logger.info("❌ This should not succeed")
    except ValidationError as e:
        logger.info(
            f"✅ Validation correctly caught nodes error: {e.errors()[0]['msg']}"
        )

    # Invalid cpus_per_task (too high)
    logger.info("Testing invalid CPUs per task...")
    try:
        invalid_config = SlurmConfig(
            queue="general",
            command="python run_model.py",
            cpus_per_task=129,  # Max is 128
            time_limit="01:00:00",
        )
        logger.info("❌ This should not succeed")
    except ValidationError as e:
        logger.info(
            f"✅ Validation correctly caught cpus_per_task error: {e.errors()[0]['msg']}"
        )

    logger.info(
        "Key concepts: Pydantic validation, error handling, configuration safety"
    )


def main():
    """Run all SLURM backend examples."""
    logger.info("🚀 ROMPY SLURM Backend Examples")
    logger.info("================================")
    logger.info(
        "These examples demonstrate how to use ROMPY with SLURM clusters for HPC jobs."
    )
    logger.info(
        "Each example builds on the previous one to show increasingly sophisticated usage."
    )
    logger.info("")

    # Run examples
    examples = [
        example_slurm_basic,
        example_slurm_advanced,
        example_slurm_with_custom_command,
        example_slurm_from_dict,
        example_slurm_validation,
    ]

    completed_examples = 0
    for i, example in enumerate(examples, 1):
        try:
            logger.info(f"Running example {i}/{len(examples)}...")
            example()
            completed_examples += 1
            logger.info("")
        except Exception as e:
            logger.error(f"❌ Example {example.__name__} failed: {e}")
            logger.info("")

    logger.info("=" * 60)
    logger.info(
        f"🎉 SLURM examples completed! ({completed_examples}/{len(examples)} examples ran successfully)"
    )
    logger.info("=" * 60)
    logger.info("What you learned:")
    logger.info("• Basic SLURM execution with SlurmConfig")
    logger.info("• Advanced SLURM parameters: queues, nodes, tasks, resources")
    logger.info("• Custom commands and environment variables")
    logger.info("• Configuration from dictionaries")
    logger.info("• Built-in validation for SLURM configurations")
    logger.info("")
    logger.info("Next steps:")
    logger.info("1. Review the SlurmConfig documentation for all available parameters")
    logger.info("2. Try these configurations in your actual SLURM environment")
    logger.info("3. Create your own SLURM configuration files for your models")
    logger.info(
        "4. Combine with other ROMPY features like postprocessing and pipelines"
    )


if __name__ == "__main__":
    main()

