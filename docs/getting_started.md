# Getting Started with Rompy

Welcome to Rompy! This guide provides a comprehensive introduction to help you get started with installing Rompy, understanding its core concepts, and running your first model simulation.

## What is Rompy?

Rompy (Relocatable Ocean Modelling in PYthon) is a Python library that streamlines the setup, configuration, execution, and analysis of coastal ocean models. It combines templated model configuration with powerful xarray-based data handling and pydantic validation, enabling users to efficiently generate model control files and input datasets for a variety of ocean and wave models.

### What can Rompy do for you?

- **Simplify model configuration**: Use Python objects to define your ocean model setup instead of complex text files.
- **Integrate diverse data sources**: Seamlessly combine various data formats and sources for model forcing.
- **Execute across platforms**: Run your models locally, in Docker containers, or on HPC systems with the same configuration.
- **Ensure reproducibility**: Serialize and version-control your model configurations for reproducible science.
- **Scale your workflows**: Move from single model runs to complex workflows with multiple coupled models.

---

## Installation

### Prerequisites

Before installing Rompy, ensure you have:

- Python 3.10 or higher
- `pip` package manager
- Basic knowledge of Python and command-line tools.
- An understanding of ocean modeling concepts (e.g., grids, boundary conditions, forcing data).

### Virtual Environment

We strongly recommend using a virtual environment to avoid dependency conflicts:

```bash
# Create a virtual environment
python -m venv rompy_env

# Activate the environment
# On Linux/macOS:
source rompy_env/bin/activate
# On Windows:
.\rompy_env\Scripts\activate
```

### Install from PyPI

The easiest way to install Rompy is from PyPI:

```bash
pip install rompy
```

To verify your installation, try importing Rompy:

```python
import rompy
print(f"Rompy version: {rompy.__version__}")
```

---

## Core Concepts

Rompy is built around a few core components that work together to define and execute a model simulation. Understanding these is key to using Rompy effectively.

1.  **`ModelRun`**: This is the central orchestrator. It holds all the information about a simulation, including when it runs, what configuration it uses, and where the output goes.
2.  **`TimeRange`**: A simple object that defines the temporal domain of your simulation: a start date, an end date, and an interval.
3.  **`Config`**: This Pydantic model holds all the model-specific settings, such as physics parameters, numerical schemes, and grid definitions. Each model (like SWAN or SCHISM) will have its own `Config` object.
4.  **`Backend`**: This determines *how* and *where* your model executes. You can run the same `ModelRun` on your local machine (`LocalConfig`), in a Docker container (`DockerConfig`), or on an HPC system, just by switching out the backend.

---

## Your First Model Run

This example demonstrates a simple model configuration from setup to execution.

### 1. Define Your Configuration

First, we define the components of our simulation in Python. We'll use the core Rompy objects to set up a simple run.

```python
from rompy.model import ModelRun
from rompy.core.config import BaseConfig
from rompy.core.time import TimeRange
from datetime import datetime

# Create a basic model configuration
# In a real use case, you would use a model-specific config like SwanConfig
config = BaseConfig()
print('Created BaseConfig')

# Create a time range for the simulation
time_range = TimeRange(
    start=datetime(2023, 1, 1),     # Start time of the simulation
    end=datetime(2023, 1, 2),       # End time of the simulation
    interval=\'1H\',                  # Time interval between outputs
)
print(f'Created TimeRange from {time_range.start} to {time_range.end} with {time_range.interval} interval')

# Create a model run instance to bring everything together
run = ModelRun(
    run_id=\'my_first_run\',              # Unique identifier for this run
    period=time_range,                  # The time period object
    config=config,                      # The configuration object
    output_dir=\'./output\',              # Directory for output files
)
print(f'Created ModelRun with ID: {run.run_id}')
print(f'Output directory: {run.output_dir}')
```

### 2. Generate the Workspace

With the `ModelRun` object defined, Rompy can generate the necessary model input files and directory structure.

```python
# This command renders the configuration into the model\'s native input file format
run.generate()
print('Generated model workspace')
```

### 3. Execute the Model

Finally, we can execute the simulation. We choose a `backend` to define the execution environment. Here, we use the `LocalConfig` to run a command on the local machine.

*Note: In a real simulation, the `command` would be the actual model executable (e.g., `swanrun`). For this example, we use `ls -l` to demonstrate that the command is run inside the generated workspace.*

```python
from rompy.backends import LocalConfig

# Define the execution backend
backend_config = LocalConfig(
    timeout=3600,                  # Maximum runtime in seconds
    command=\'ls -l\',               # The command to execute
)

# Run the simulation
success = run.run(backend=backend_config)

if success:
    print('Model run completed successfully!')
else:
    print('Model run failed.')
```

---

## Next Steps

Now that you have a basic understanding of the Rompy workflow, you are ready to explore more advanced topics:

- **[Progressive Tutorials](progressive_tutorials.md)**: Follow our step-by-step tutorials to learn about grids, data sources, and more complex workflows.
- **[Models](models.md)**: Dive into guides for specific models like SWAN and SCHISM.
- **[Configuration Deep Dive](configuration_deep_dive.md)**: Learn about advanced configuration techniques.
- **[Backends](backends.md)**: Explore different execution backends like Docker and HPC.
