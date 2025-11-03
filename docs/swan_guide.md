# SWAN Model Guide

This guide provides detailed information about using the SWAN (Simulating WAves Nearshore) model with Rompy, including configuration examples, best practices, and troubleshooting tips.

## Overview of SWAN with Rompy

SWAN is a third-generation wind-wave model that computes random, short-crested waves in coastal regions and inland waters. With Rompy, you can configure SWAN simulations using Python objects that are validated with Pydantic, ensuring consistent and reproducible model setups.

## SWAN Configuration

SWAN configurations in Rompy typically include:

- Grid definition (structured or unstructured)
- Time settings
- Physics parameters
- Boundary conditions
- Output specifications

### Basic SWAN Configuration Example

```python
from rompy.model import ModelRun
from rompy.core.time import TimeRange
from rompy.core.grid import RegularGrid
from datetime import datetime

# Define your SWAN-specific grid
swan_grid = RegularGrid(
    lon_min=-75.0,
    lon_max=-65.0,
    lat_min=35.0,
    lat_max=45.0,
    dx=0.1,
    dy=0.1,
)

# Time settings for the simulation
time_range = TimeRange(
    start=datetime(2023, 6, 1, 0),
    end=datetime(2023, 6, 7, 0),  # One week simulation
    interval="1H"  # Hourly outputs
)

# SWAN-specific configuration (conceptual - actual class would be in rompy-swan plugin)
# swan_config = SWANConfig(
#     grid=swan_grid,
#     physics=SWANPhysics(
#         gen="KOMEN",
#         wndr="RAY",
#         depth="MDS",
#     ),
#     boundaries=SWANBoundaries(
#         # Define your boundary conditions
#     ),
#     output=SWANOutput(
#         # Define your output settings
#     ),
# )

# Create a model run with SWAN configuration
# model_run = ModelRun(
#     run_id="swan_example",
#     period=time_range,
#     config=swan_config,
#     output_dir="./swan_output",
# )

# Generate SWAN input files
# staging_dir = model_run.generate()
# print(f"SWAN model files generated at: {staging_dir}")
```

## Advanced SWAN Configuration

### Grid Configuration

SWAN supports both structured and unstructured grids. In Rompy, you would typically use:

- `RegularGrid` for regular rectangular grids
- `CurvilinearGrid` for curvilinear grids
- `UnstructuredGrid` for unstructured grids (if supported)

### Boundary Conditions

SWAN boundary conditions can be specified in various formats:

1. **Station-based boundaries**: Point measurements at specific locations
2. **Spectrum boundaries**: Full spectral information
3. **Parameter boundaries**: Significant wave height, peak period, etc.

```python
# Conceptual example of boundary conditions
# boundary_stations = [
#     SWANBoundaryStation(
#         name="boundary_1",
#         position=[-74.5, 40.0],
#         timeseries=BoundaryTimeseries(
#             hsig=[1.2, 1.5, 1.8],  # Significant wave heights
#             tm02=[8.5, 9.0, 9.5],  # Mean zero-crossing periods
#             dir=[180, 185, 190],    # Mean wave directions
#             tph=[8.0, 8.5, 9.0],   # Peak period
#         ),
#     ),
#     # Add more boundary stations as needed
# ]
```

### Physics Settings

SWAN offers various physics options that can be configured:

- Generation: Specify the wind-wave generation model (e.g., Komen, Janssen)
- Dissipation: Define how energy is lost (e.g., whitecapping, bottom friction)
- Depth-induced breaking: Select the wave breaking model
- Triad interactions: Configure 3-wave interactions

### Output Configuration

Configure SWAN outputs based on your needs:

- Global parameters (significant wave height, mean period, etc.)
- Spectral output at specific points
- 2D parameter fields
- Time series at specific locations

## Running SWAN with Different Backends

### Local Execution

```python
# from rompy.backends import LocalConfig

# backend_config = LocalConfig(
#     timeout=14400,  # 4 hours
#     command="swanrun -input swaninit.cgd",
#     env_vars={"SWAN_DIR": "/path/to/swan"},
# )

# success = model_run.run(backend=backend_config)
# print(f"SWAN local execution: {'Success' if success else 'Failed'}")
```

### Docker Execution

```python
# from rompy.backends import DockerConfig

# docker_config = DockerConfig(
#     image="rompy/swan:latest",
#     timeout=28800,  # 8 hours
#     cpu=8,
#     memory="16g",
#     volumes=[f"{model_run.output_dir}:/output:rw"],
# )

# success = model_run.run(backend=docker_config)
# print(f"SWAN Docker execution: {'Success' if success else 'Failed'}")
```

## Best Practices

1. **Grid Resolution**: Balance resolution with computational cost. Finer grids provide better accuracy but longer runtimes.

2. **Time Stepping**: Choose appropriate time steps. For most SWAN simulations, the time step should be small enough to properly represent wave propagation.

3. **Boundary Conditions**: Ensure boundary conditions are consistent with your application. For example, if you're modeling storm waves, ensure your boundaries capture the storm's characteristics.

4. **Physics Selection**: Choose physics options appropriate for your study area. For example, include wave-current interaction if there are significant currents.

5. **Validation**: Always validate your model setup against available observations before using it for prediction.

## Common Issues and Troubleshooting

### Model Crashes

- Check input files for errors
- Verify grid definitions (no negative depths, proper orientation)
- Ensure boundary data is available for the entire simulation period

### Incorrect Results

- Validate boundary conditions against known values
- Check that physics options are appropriate for the study area
- Verify that the grid resolution is adequate

### Performance Issues

- Consider coarsening the grid or reducing simulation time
- Optimize physics options (simplify where possible)
- Use appropriate parallelization settings

## Next Steps

- Review the [Backends Guide](backends.md) for detailed execution options
- Learn about [Configuration Deep Dive](configuration_deep_dive.md) for detailed configuration options
- Check the [Progressive Tutorials](progressive_tutorials.md) for practical examples