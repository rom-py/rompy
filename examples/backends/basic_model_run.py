#!/usr/bin/env python3
"""
Basic ModelRun Configuration for Backend Testing

This script creates a simple ModelRun configuration that can be used to test
different backend configurations (local, docker, slurm).
"""

import tempfile
from datetime import datetime
from pathlib import Path

from rompy.core.time import TimeRange
from rompy.model import ModelRun


def create_basic_model_run():
    """
    Create a basic model run configuration for testing backends.
    This creates a minimal model run that can execute a simple command
    using different backends.
    """
    # Create a temporary directory for output
    temp_dir = Path(tempfile.mkdtemp(prefix="rompy_test_"))
    
    # Create a basic model run
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


if __name__ == "__main__":
    # Create the basic model run
    model = create_basic_model_run()
    
    print("Basic ModelRun Configuration Created")
    print("="*40)
    print(f"Run ID: {model.run_id}")
    print(f"Output Directory: {model.output_dir}")
    print(f"Time Period: {model.period.start} to {model.period.end}")
    print(f"Time Interval: {model.period.interval}")
    print(f"Delete Existing: {model.delete_existing}")
    print()
    print("This basic configuration can be used to test different backends.")
    print("For example:")
    print("  - Local backend: Executes commands on the local machine")
    print("  - Docker backend: Runs commands in Docker containers")
    print("  - SLURM backend: Submits jobs to HPC clusters")