# Progressive Tutorials

This section contains a series of progressive tutorials that gradually introduce more complex concepts. Each tutorial builds on the previous one, creating a learning path from basic usage to advanced features. If you're new to Rompy, you may want to start with the [Getting Started Guide](getting_started.md).

## Understanding Rompy Components

Rompy is a Python package for generating configuration files and forcing data for numerical wave and wave-climate models. The core architecture consists of several key components:

### ModelRun
Combines all components and generates a simulation workspace ready to run.
- **Key Attributes**: `run_id`, `period` (TimeRange), `config`, `output_dir`
- **Methods**: `run()` - Executes the model simulation

### Grid
Defines the spatial domain and resolution.
- **Types**:
  - `RegularGrid`: Uniform spacing in x and y directions
  - `UnstructuredGrid`: Non-uniform mesh (if supported)
- **Key Attributes**: `x0`, `y0`, `nx`, `ny`, `dx`, `dy`

### TimeRange
Specifies the temporal domain of the simulation.
- **Key Attributes**: `start`, `end`, `interval`

### Data Sources
Provides input data for the model.
- **Types**:
  - `DataGrid`: For gridded model inputs
  - `DataPoint`: For point-based time series data
  - `DataBlob`: For generic file-based data
- **Components**: Bathymetry, Wind, Boundary conditions, Other environmental variables

### Config
Holds model-specific configuration settings.
- **Types**: Model-specific configs (e.g., `SwanConfig`, `SCHISMConfig`)
- **Key Components**: Physics parameters, Numerical scheme settings, Output specifications

### Source
Defines data sources for model inputs.
- **Types**:
  - `SourceFile`: For file-based data sources
  - `SourceIntake`: For intake catalog-based data
  - `SourceDatamesh`: For Datamesh-based data
- **Components**: URI/path to data, variable mappings, coordinate definitions

### Output
Defines what data to save from the model run.
- **Components**: Variables to output, Output locations, Output frequency

## Tutorial 1: Grid Configuration and Visualization

In this first tutorial, we'll explore grid configuration and visualization capabilities of Rompy:

```python
from rompy.core.grid import RegularGrid
from pathlib import Path

# Create a RegularGrid for an area off the west coast of Australia
grid = RegularGrid(
    x0=110.0,  # Longitude of the lower-left corner
    y0=-35.2,  # Latitude of the lower-left corner
    rot=4.0,   # Rotation angle in degrees
    dx=0.5,    # Grid spacing in the x-direction (degrees)
    dy=0.5,    # Grid spacing in the y-direction (degrees)
    nx=15,     # Number of grid points in the x-direction
    ny=25,     # Number of grid points in the y-direction
)

# Each grid has a bbox and a plot method
print("Grid bounding box:", grid.bbox())

# The grid can be plotted directly
# grid.plot()  # Uncomment to visualize
```

## Tutorial 2: Working with Data Sources

Now let's work with data sources to extract relevant oceanographic data:

```python
from rompy.core.data import DataGrid
from rompy.core.source import SourceFile
from rompy.core.time import TimeRange

# Define a data source for bathymetry
# For this example, we'll use a sample GEBCO file (you would replace with your actual path)
bathymetry_source = SourceFile(uri="path/to/gebco_bathymetry.nc")

# Create a DataGrid object for bathymetry
gebco_grid = DataGrid(
    id="gebco_bathymetry",
    source=bathymetry_source,
    variables=["elevation"],
    coords={"y": "lat", "x": "lon"},
)

# Extract bathymetry data for our grid
workdir = Path("./output_bathymetry")
workdir.mkdir(exist_ok=True)

# Output will be the path to the extracted data file
output = gebco_grid.get(grid=grid, destdir=workdir)
print(f"Bathymetry data extracted to: {output}")
```

## Tutorial 3: Time-Series Data Extraction

Let's work with time-series data, such as atmospheric forcing:

```python
# Create a TimeRange for our simulation period
timerange = TimeRange(
    start="2023-01-01T00:00:00",
    end="2023-01-02T00:00:00",
    interval="1H",  # Hourly intervals
)

# Define a source for time-varying data (e.g., ERA5 wind data)
wind_source = SourceFile(uri="path/to/era5_wind.nc")

# Create a DataGrid for wind forcing
from rompy.core.filters import Filter

era5_forcing = DataGrid(
    id="era5_wind",
    source=wind_source,
    variables=["u10", "v10"],  # 10m wind components
    coords={"t": "time", "y": "latitude", "x": "longitude"},
    # Use filter to handle coordinate issues (like reversed latitude)
    filter=Filter(sort=dict(coords=["latitude"])),
)

# Extract wind data for our grid and time range
wind_output = era5_forcing.get(grid=grid, time=timerange, destdir=workdir)
print(f"Wind data extracted to: {wind_output}")
```

## Tutorial 4: Boundary Condition Data

For wave models, we often need boundary conditions from spectral data:

```python
from rompy.core.boundary import BoundaryWaveStation

# Create a boundary dataset from spectra data
boundary_stations = BoundaryWaveStation(
    id="ww3_boundary",
    source=SourceFile(uri="path/to/spec_data.nc"),
    sel_method="idw",  # Inverse distance weighting selection method
    sel_method_kwargs={
        "tolerance": 4  # Distance tolerance for selection
    },
)

# Extract boundary condition data along the grid boundary
boundary_output = boundary_stations.get(grid=grid, time=timerange, destdir=workdir)
print(f"Boundary data extracted to: {boundary_output}")
```

## Tutorial 5: Basic ModelRun Configuration

Now let's create a basic model configuration using Rompy's core components:

```python
from rompy.model import ModelRun
from rompy.core.config import BaseConfig

# Create a basic configuration
config = BaseConfig(
    template="path/to/model_template",
    checkout="path/to/model_checkout",
    grid=grid,  # Include the grid we defined earlier
)

# Create a model run
model_run = ModelRun(
    run_id="progressive_tutorial_run",
    period=timerange,  # Use the time range we defined earlier
    config=config,
    output_dir="./model_output",
)

# Generate the model input files
staging_dir = model_run.generate()
print(f"Model files generated at: {staging_dir}")
```

## Tutorial 6: Complete Workflow with Data Integration

Let's create a more complete example that integrates multiple data sources:

```python
from pathlib import Path
import tempfile

# Create a temporary workspace
workdir = Path("./integrated_output")
workdir.mkdir(exist_ok=True)

# Define our area and time range
grid = RegularGrid(
    x0=110.0,
    y0=-35.2,
    rot=4.0,
    dx=0.5,
    dy=0.5,
    nx=15,
    ny=25,
)

timerange = TimeRange(
    start="2023-01-01T00:00:00",
    end="2023-01-02T00:00:00",
    interval="1H",
)

# Create multiple data sources
bathy_source = DataGrid(
    id="gebco_bathy",
    source=SourceFile(uri="path/to/bathy.nc"),
    variables=["elevation"],
    coords={"y": "lat", "x": "lon"},
)

wind_source = DataGrid(
    id="era5_wind",
    source=SourceFile(uri="path/to/wind.nc"),
    variables=["u10", "v10"],
    coords={"t": "time", "y": "latitude", "x": "longitude"},
    filter=Filter(sort=dict(coords=["latitude"])),
)

# Extract data for our model domain
bathy_output = bathy_source.get(grid=grid, destdir=workdir)
wind_output = wind_source.get(grid=grid, time=timerange, destdir=workdir)

print(f"Bathymetry data: {bathy_output}")
print(f"Wind data: {wind_output}")

# Now create a model configuration that uses this data
config = BaseConfig(
    template="path/to/model_template",
    checkout="path/to/model_checkout",
    grid=grid,
)

model_run = ModelRun(
    run_id="integrated_workflow",
    period=timerange,
    config=config,
    output_dir=workdir / "model_outputs",
)

# Generate inputs
staging_dir = model_run.generate()
print(f"Generated model files at: {staging_dir}")
```

## Tutorial 7: Model Execution with Different Backends

Now let's run our model using different execution backends:

```python
from rompy.backends import LocalConfig

# Execute with local backend
local_config = LocalConfig(
    timeout=3600,
    command="your_model_executable",
    env_vars={"OMP_NUM_THREADS": "4"},
)

# Run the model
success = model_run.run(backend=local_config)
print(f"Execution status: {'Success' if success else 'Failed'}")
```

## Tutorial 8: Using YAML Configuration Files

One of the key advantages of Rompy's schema-based approach is the ability to represent complex model configurations as transportable YAML files.

### Exporting to YAML

You can programmatically generate YAML from a Python configuration:

```python
# Export the complete model configuration to YAML
yaml_content = model_run.model_dump_yaml()
print("YAML Configuration:")
print(yaml_content)

# Or save directly to a file
config_file = workdir / "model_config.yaml"
with open(config_file, "w") as f:
    f.write(yaml_content)
print(f"Configuration saved to: {config_file}")
```

### Loading from YAML

To use a YAML configuration in Python:

```python
from rompy.model import ModelRun

# Load the configuration from YAML
with open(config_file, "r") as f:
    yaml_content = f.read()

# Create the model run from YAML
loaded_model_run = ModelRun.model_validate_yaml(yaml_content)

# Use it just like the original
staging_dir = loaded_model_run.generate()
print(f"Generated from YAML at: {staging_dir}")
```

### Running with Command Line Interface

Once you have your YAML configuration, you can run it using Rompy's CLI:

```bash
rompy run --config model_config.yaml
```

To specify a different backend:

```bash
rompy run --config model_config.yaml --backend-config local_backend.yml
```

For more information about available CLI options, see the [CLI Reference](cli.md).

## Tutorial 9: Advanced Data Processing

Working with real-world data often requires more sophisticated data processing techniques:

```python
# For boundary condition data, you can extract and interpolate
# data to specific grid boundary points using various methods

boundary_data = BoundaryWaveStation(
    id="boundary_conditions",
    source=SourceFile(uri="path/to/boundary_data.nc"),
    sel_method="idw",  # Use inverse distance weighting
    sel_method_kwargs={"tolerance": 4.0},
)

# Extract boundary data for our grid and time period
boundary_output = boundary_data.get(
    grid=grid,
    time=timerange,
    destdir=workdir
)

print(f"Boundary conditions extracted to: {boundary_output}")
```

## Model-Specific Tutorials

For model-specific tutorials on SWAN, SCHISM, and other supported models, see the [Model Guides](models.md).

## Next Steps

- Explore [Configuration Deep Dive](configuration_deep_dive.md) for detailed configuration options
- Learn about [Common Workflows](common_workflows.md) for best practices
- Check out the [Advanced Topics](backends.md) for more complex usage
- Review the [API Reference](api.md) for comprehensive documentation of all classes and methods