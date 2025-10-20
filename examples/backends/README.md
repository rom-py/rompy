# ROMPY SLURM Backend Examples

This directory contains examples of how to use ROMPY with SLURM for HPC cluster execution.

## Examples

### 05_slurm_backend_run.py
A comprehensive tutorial showing different ways to configure and use the SLURM backend:

- Basic SLURM execution
- Advanced SLURM configuration with multiple parameters
- Custom commands on SLURM
- Creating configurations from dictionaries
- Configuration validation

Run the example:
```bash
python 05_slurm_backend_run.py
```

## Configuration Files

### slurm_backend.yml
A basic configuration file for running jobs on SLURM with minimal parameters.

### slurm_backend_examples.yml
A collection of different SLURM configuration examples:
- Basic SLURM configuration
- Advanced GPU job configuration 
- High-memory job configuration
- Custom working directory configuration

## Key Features

The ROMPY SLURM backend supports:

- **Resource allocation**: Specify nodes, tasks, and CPU cores
- **Queue/partition selection**: Run on different SLURM partitions
- **Time limits**: Set job time limits in HH:MM:SS format
- **Environment variables**: Set environment variables for your job
- **Job notifications**: Email notifications on job start/end/failure
- **Custom commands**: Run custom commands instead of the default model run
- **Additional SLURM options**: Pass any additional SLURM options via `additional_options`
- **GPU resources**: Support for GPU allocation via `--gres` options

## Usage

To use the SLURM backend in your application:

```python
from rompy.backends import SlurmConfig
from rompy.model import ModelRun

# Create SLURM configuration
config = SlurmConfig(
    queue="gpu",                    # SLURM partition
    nodes=2,                        # Number of nodes
    ntasks=8,                       # Number of tasks
    cpus_per_task=4,               # CPU cores per task
    time_limit="02:00:00",         # Time limit
    account="research_project",     # Account for billing
    additional_options=["--gres=gpu:v100:2"],  # GPU allocation
)

# Create and run your model
model = ModelRun(...)
model.run(backend=config)
```

## Validation

The SLURM backend includes comprehensive validation:
- Time limit format validation (HH:MM:SS)
- Bounds checking for nodes, CPUs, etc.
- Required field validation