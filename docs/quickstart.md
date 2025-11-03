---
execute: true
---

# Quickstart Guide

This guide will help you get up and running with Rompy quickly. For more detailed information, check out our [User Guide](user_guide.md).

## Installation

### Install from PyPI

The easiest way to install Rompy is from PyPI:

```bash
pip install rompy
```

### Install from source code

If you want the latest development version:

```bash
git clone git@github.com:rom-py/rompy.git
cd rompy
pip install -e .
```

## Your First Model Run

This example demonstrates a simple model configuration using real Rompy classes. Since this documentation is built with the actual Rompy library available, you can see how the real API works:

```python
from rompy.model import ModelRun
from rompy.core.config import BaseConfig
from rompy.core.time import TimeRange
from datetime import datetime

# Create a basic model configuration
config = BaseConfig(
    template='path/to/your/template',  # Path to your model template
    checkout='path/to/checkout',      # Path where model files will be generated
)
print('Created BaseConfig with template and checkout paths')

# Create a time range for the simulation
time_range = TimeRange(
    start=datetime(2023, 1, 1),     # Start time of the simulation
    end=datetime(2023, 1, 2),       # End time of the simulation
    interval='1H',                  # Time interval between outputs
)
print(f'Created TimeRange from {time_range.start} to {time_range.end} with {time_range.interval} interval')

# Create a model run instance
run = ModelRun(
    run_id='my_first_run',              # Unique identifier for this run
    period=time_range,                  # The time period object
    config=config,                      # The configuration object
    output_dir='./output',              # Directory for output files
)
print(f'Created ModelRun with ID: {run.run_id}')
print(f'Output directory: {run.output_dir}')
```

The actual model generation and execution would require real model executables and data sources. Here's how you would complete the actual workflow:

```python
# Generate model input files (this requires actual templates)
# run.generate()

# Execute the model run with a local backend (this requires actual model executables)
# from rompy.backends import LocalConfig
# backend_config = LocalConfig(
#     timeout=3600,                  # Maximum runtime in seconds
#     command='your_model_executable',  # Command to run your model
# )
# success = run.run(backend=backend_config)

# if success:
#     print('Model run completed successfully!')
# else:
#     print('Model run failed.')
```

## Understanding the Components

1. **ModelRun**: The main class that manages your model execution. It handles the time period, output locations, and configuration.

2. **TimeRange**: Defines when your model simulation starts and ends, and the time interval for outputs.

3. **BaseConfig**: A basic configuration object that you can extend or replace with more specific model configurations.

4. **Backend Configuration**: Determines how and where your model runs (locally, in Docker, on HPC, etc.).

## Next Steps

For more detailed information about Rompy concepts and usage:

- Follow our [Complete User Guide](user_guide.md)
- Explore the [Core Concepts](core_concepts.md) to understand the fundamental components 
- Check out the [Progressive Tutorials](progressive_tutorials.md) for a structured learning path
- Get started with [Configuration Deep Dive](configuration_deep_dive.md) for detailed configuration options

For real ocean modeling examples, see the [Examples](examples.md) section and the `examples/` directory in the repository.