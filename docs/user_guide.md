# User Guide

Welcome to the Rompy User Guide! This section provides everything you need to get started with Rompy, from installation to running your first ocean model simulations.

## What is Rompy?

Rompy (Relocatable Ocean Modelling in PYthon) is a Python library that streamlines the setup, configuration, execution, and analysis of coastal ocean models. It combines templated model configuration with xarray-based data handling and pydantic validation, enabling users to efficiently generate model control files and input datasets for a variety of ocean and wave models.

## What can Rompy do for you?

- **Simplify model configuration**: Use Python objects to define your ocean model setup instead of complex text files
- **Integrate diverse data sources**: Seamlessly combine various data formats and sources for model forcing
- **Execute across platforms**: Run your models locally, in Docker containers, or on HPC systems with the same configuration
- **Ensure reproducibility**: Serialize and version-control your model configurations for reproducible science
- **Scale your workflows**: Move from single model runs to complex workflows with multiple coupled models

## Prerequisites

Before starting, ensure you have:

- Python 3.10 or higher
- Basic knowledge of Python and command line tools
- Understanding of ocean modeling concepts (grid, boundary conditions, forcing data, etc.)

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

Let's run through a complete example that demonstrates the typical workflow:

### Define Your Model Configuration

First, create a basic model configuration for a simple simulation:

```python
from rompy.model import ModelRun
from rompy.core.config import BaseConfig
from rompy.core.time import TimeRange
from datetime import datetime

# Define the time period for your model run
time_range = TimeRange(
    start=datetime(2023, 1, 1),
    end=datetime(2023, 1, 2),
    interval="1H"
)

# Create a basic configuration
config = BaseConfig(
    template="path/to/your/model/template",  # Path to your model template files
    checkout="path/to/model/files",         # Where to place generated files
)

# Create your model run
model_run = ModelRun(
    run_id="my_first_simulation",
    period=time_range,
    config=config,
    output_dir="./simulations",
)
```

### Generate Model Input Files

Generate the necessary input files for your simulation:

```python
# Generate model input files based on the configuration
staging_dir = model_run.generate()
print(f"Model files generated at: {staging_dir}")
```

### Execute the Model

Run your model using a backend (in this example, we'll use the local backend):

```python
from rompy.backends import LocalConfig

# Configure the backend
backend_config = LocalConfig(
    timeout=3600,  # Time out after 1 hour
    command="your_model_executable",  # Replace with your actual model command
)

# Execute the model
success = model_run.run(backend=backend_config)

if success:
    print("Model run completed successfully!")
else:
    print("Model run failed.")
```

### Post-process Results

After the model run, you might want to process the results:

```python
# Process the output files
results = model_run.postprocess(processor="noop")  # or your preferred processor
print(f"Post-processing results: {results}")
```

## Understanding Core Concepts

Rompy is built around several core components:

### ModelRun

The `ModelRun` class is the central orchestrator that manages the entire model execution process. It coordinates model generation, execution, and post-processing.

### Configuration System

The configuration system uses Pydantic models to provide type safety and validation:
- `BaseConfig`: The foundational configuration model
- Model-specific configurations inherit from or extend BaseConfig
- Grid, data, and source configurations define the spatial domain and data inputs

### Grid Configuration

Grids form a core component of any model. Rompy provides:
- `BaseGrid`: A base class for grids
- `RegularGrid`: For regular rectangular grids
- Support for other grid types will be added in the future

### Data and Source Configuration

Data objects represent data inputs into the model with different source types:
- `SourceBase`, `SourceFile`, `SourceIntake`: Different ways to access data
- Support for local files, remote catalogs, streaming data, etc.

## Configuration Deep Dive

### ModelRun Configuration

The `ModelRun` class handles the top-level configuration:

```python
from rompy.model import ModelRun
from rompy.core.time import TimeRange
from datetime import datetime

# Create a model run with comprehensive settings
model_run = ModelRun(
    run_id="detailed_example",                    # Unique identifier for this run
    period=TimeRange(
        start=datetime(2023, 1, 1),
        end=datetime(2023, 1, 7),
        interval="1H"
    ),                                           # Define the time period
    config=your_config,                          # Model-specific configuration
    output_dir="./simulations",                  # Where to save output
    delete_existing=True,                        # Delete existing output directory
    run_id_subdir=True,                          # Use run_id as a subdirectory
)
```

### Grid Configuration

Define the spatial domain of your model:

```python
from rompy.core.grid import RegularGrid

# Regular grid
regular_grid = RegularGrid(
    lon_min=-75.0,
    lon_max=-65.0,
    lat_min=35.0,
    lat_max=45.0,
    dx=0.1,        # Longitude resolution
    dy=0.1,        # Latitude resolution
)
```

### Data Configuration

Represent input data for your model:

```python
from rompy.core.data import DataGrid
from rompy.core.source import SourceFile, SourceIntake

# Data from a local file
local_source = SourceFile(
    uri="path/to/data.nc",
    driver="netcdf",
)

local_data = DataGrid(
    source=local_source,
    var_map={"significant_wave_height": "swh"},
)

# Data from an intake catalog
remote_source = SourceIntake(
    catalog="https://catalog.example.com/catalog.yml",
    entry="model_data",
)

remote_data = DataGrid(
    source=remote_source,
    var_map={"eastward_velocity": "u", "northward_velocity": "v"},
)
```

## Next Steps

Now that you've learned the basics, explore these resources to deepen your understanding:

1. **[Progressive Tutorials](progressive_tutorials.md)**: Follow a structured learning path from basic to advanced concepts
2. **[Models](models.md)**: Understand how to work with specific ocean models like SWAN and SCHISM
3. **[Backends](backends.md)**: Learn about different execution environments
4. **[Plugin Architecture](plugin_architecture.md)**: Understand how to extend Rompy for your needs