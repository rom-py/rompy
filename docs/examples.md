# Practical Examples

This section provides real-world ocean modeling scenarios to help you understand how to use Rompy for different use cases. These examples build on the concepts introduced in the [Progressive Tutorials](progressive_tutorials.md).

## SWAN Model Example: Wave Simulation

This example demonstrates how to configure and run a simple SWAN model simulation:

```python
from rompy.model import ModelRun
from rompy.core.time import TimeRange
from datetime import datetime
from rompy.backends import LocalConfig

# Configuration for SWAN model would go here
# (This is a conceptual example - actual implementation would require SWAN-specific config)

# Define the time range for the simulation
time_range = TimeRange(
    start=datetime(2023, 1, 1),
    end=datetime(2023, 1, 2),
    interval="1H"
)

# Create a model run instance
run = ModelRun(
    run_id="swan_basic_example",
    period=time_range,
    # config=SWANConfig(...),  # SWAN-specific configuration
    output_dir="./swan_output",
)

# Generate model files
run.generate()

# Run the model with local backend
backend_config = LocalConfig(
    timeout=7200,  # 2 hours
    command="swanrun -input swaninit.cgd"  # SWAN execution command
)
success = run.run(backend=backend_config)

if success:
    print("SWAN model completed successfully!")
```

## SCHISM Model Example: Hydrodynamics

This example demonstrates how to set up a simple SCHISM model simulation:

```python
from rompy.model import ModelRun
from rompy.core.time import TimeRange
from datetime import datetime
from rompy.backends import LocalConfig

# Configuration for SCHISM model would go here
# (This is a conceptual example - actual implementation would require SCHISM-specific config)

# Define the time range for the simulation
time_range = TimeRange(
    start=datetime(2023, 1, 1),
    end=datetime(2023, 1, 10),  # 10-day simulation
    interval="1D"  # Daily outputs
)

# Create a model run instance
run = ModelRun(
    run_id="schism_basic_example",
    period=time_range,
    # config=SCHISMConfig(...),  # SCHISM-specific configuration
    output_dir="./schism_output",
)

# Generate model files
run.generate()

# Run the model with local backend
backend_config = LocalConfig(
    timeout=14400,  # 4 hours
    command="mpirun -np 4 schism -i hstime.nml"  # SCHISM execution command
)
success = run.run(backend=backend_config)

if success:
    print("SCHISM model completed successfully!")
```

## Advanced Example: Coupled Ocean-Atmosphere Forcing

This example shows how to configure a model with multiple data sources for boundary conditions:

```python
from rompy.model import ModelRun
from rompy.core.time import TimeRange
from rompy.core.grid import RegularGrid
from rompy.core.data import DataGrid, DataBoundary
from datetime import datetime

# Define a regular grid for our model domain
grid = RegularGrid(
    lon_min=-75.0,
    lon_max=-65.0,
    lat_min=35.0,
    lat_max=45.0,
    dx=0.1,
    dy=0.1,
)

# Configure multiple data sources
wave_data = DataBoundary(
    source="waves",
    # source_config=...  # Configuration for wave boundary data
)

ocean_data = DataGrid(
    source="ocean_currents",
    # source_config=...  # Configuration for ocean current data
)

# Define the time range for the simulation
time_range = TimeRange(
    start=datetime(2023, 6, 1),
    end=datetime(2023, 6, 7),  # 7-day simulation
    interval="1H"  # Hourly outputs
)

# Create a model run instance with multiple data sources
run = ModelRun(
    run_id="coupled_forcing_example",
    period=time_range,
    # config=ModelConfig(
    #     grid=grid,
    #     boundary_conditions=[wave_data, ocean_data],
    #     # ... other configuration
    # ),
    output_dir="./coupled_output",
)

# Generate model files with all data sources
run.generate()

# Execute with Docker backend
from rompy.backends import DockerConfig
docker_config = DockerConfig(
    image="rompy/model:latest",
    timeout=28800,  # 8 hours
    cpu=8,
    memory="16g",
    volumes=["./coupled_output:/output:rw"],
)
success = run.run(backend=docker_config)

if success:
    print("Coupled model simulation completed successfully!")
```

## Data Integration Example

This example demonstrates how to integrate different data sources using Rompy's data handling:

```python
from rompy.core.data import DataGrid, DataBlob
from rompy.core.source import SourceFile, SourceIntake

# Configure a data source from local files
local_source = SourceFile(
    uri="path/to/local/data.nc",
    driver="netcdf",
    # ... additional configuration
)

# Configure a data source from a remote intake catalog
remote_source = SourceIntake(
    catalog="https://catalog.example.com/catalog.yml",
    entry="model_data",
    # ... additional configuration
)

# Create data objects with the sources
local_data = DataBlob(
    source=local_source,
    # ... additional configuration
)

remote_data = DataGrid(
    source=remote_source,
    var_map={"significant_wave_height": "swh"},
    # ... additional configuration
)

print("Data sources configured successfully!")
# These data sources can be integrated into your model configuration
```

## Real-World Workflow: Storm Surge Analysis

This example demonstrates a more realistic workflow for analyzing storm surge:

```python
from rompy.model import ModelRun
from rompy.core.time import TimeRange
from rompy.core.grid import RegularGrid
from rompy.core.data import DataGrid
from rompy.core.source import SourceIntake
from datetime import datetime

def setup_storm_surge_analysis():
    # 1. Define the model domain
    grid = RegularGrid(
        lon_min=-75.5,
        lon_max=-73.5,
        lat_min=39.0,
        lat_max=41.0,
        dx=0.025,  # Higher resolution for coastal area
        dy=0.025,
    )
    
    # 2. Define time period for the storm event
    time_range = TimeRange(
        start=datetime(2023, 9, 15),  # Before storm
        end=datetime(2023, 9, 22),    # After storm
        interval="1H"
    )
    
    # 3. Configure wind and pressure forcing data
    wind_data = DataGrid(
        source=SourceIntake(
            catalog="https://catalog.example.com/met_data.yml",
            entry="gfs_wind",
        ),
        var_map={"eastward_wind": "uwnd", "northward_wind": "vwnd"},
    )
    
    pressure_data = DataGrid(
        source=SourceIntake(
            catalog="https://catalog.example.com/met_data.yml",
            entry="gfs_pressure",
        ),
        var_map={"air_pressure": "pres"},
    )
    
    # 4. Create model configuration with forcing
    config = ModelRun(
        run_id="storm_surge_analysis",
        period=time_range,
        # config=ModelConfig(
        #     grid=grid,
        #     forcing=[wind_data, pressure_data],
        #     physics=PhysicsConfig(
        #         barotropic=True,
        #         waves=False,
        #         advection=True,
        #     ),
        # ),
        output_dir="./storm_surge_output",
    )
    
    return config

# Set up the analysis
model_run = setup_storm_surge_analysis()

# Run analysis with Docker backend for better resource management
from rompy.backends import DockerConfig
docker_config = DockerConfig(
    image="rompy/schism:latest",
    timeout=43200,  # 12 hours
    cpu=16,
    memory="32g",
    volumes=["./storm_surge_output:/output:rw"],
)

success = model_run.run(backend=docker_config)

if success:
    print("Storm surge analysis completed successfully!")
    
    # Post-process results to extract extreme water levels
    results = model_run.postprocess(processor="extremes")
    print(f"Maximum water level: {results.get('max_level', 'N/A')}")
else:
    print("Storm surge analysis failed.")
```

## Next Steps

- For more model-specific examples, see the [Model Guides](models.md) section
- Learn about configuring [Backends](backends.md) for different execution environments
- Explore the [API Reference](api.md) for detailed information about classes and methods
- Review [Common Workflows](common_workflows.md) for best practices and patterns