# SCHISM Model Guide

This guide provides detailed information about using the SCHISM (Semi-implicit Cross-scale Hydroscience Integrated System Model) with Rompy, including configuration examples, best practices, and troubleshooting tips.

## Overview of SCHISM with Rompy

SCHISM is a new unstructured-grid, multi-scale, multi-phase ocean modeling system that can simulate 3D baroclinic circulation, sediment transport, water quality, and biogeochemistry. With Rompy, you can configure SCHISM simulations using Python objects that are validated with Pydantic, ensuring consistent and reproducible model setups.

## SCHISM Configuration

SCHISM configurations in Rompy typically include:

- Grid definition (unstructured)
- Time settings
- Physics parameters
- Boundary conditions
- Initial conditions
- Output specifications

### Basic SCHISM Configuration Example

```python
from rompy.model import ModelRun
from rompy.core.time import TimeRange
from datetime import datetime

# Time settings for the simulation
time_range = TimeRange(
    start=datetime(2023, 6, 1, 0),
    end=datetime(2023, 6, 7, 0),  # One week simulation
    interval="1H"  # Hourly outputs
)

# SCHISM-specific configuration (conceptual - actual class would be in rompy-schism plugin)
# schism_config = SCHISMConfig(
#     grid=SCHISMGrid(
#         hgrid="path/to/hgrid.gr3",  # Horizontal grid file
#         vgrid="path/to/vgrid.in",   # Vertical grid file
#     ),
#     physics=SCHISMPhysics(
#         baroclinic=True,           # Include baroclinic effects
#         sediment_transport=False,  # Enable sediment transport
#         age=True,                  # Track age of water masses
#     ),
#     boundaries=SCHISMBoundaries(
#         # Define your boundary conditions
#     ),
#     initial_conditions=SCHISMInitial(
#         # Define initial conditions
#     ),
#     output=SCHISMOutput(
#         # Define your output settings
#     ),
# )

# Create a model run with SCHISM configuration
# model_run = ModelRun(
#     run_id="schism_example",
#     period=time_range,
#     config=schism_config,
#     output_dir="./schism_output",
# )

# Generate SCHISM input files
# staging_dir = model_run.generate()
# print(f"SCHISM model files generated at: {staging_dir}")
```

## Advanced SCHISM Configuration

### Grid Configuration

SCHISM uses unstructured grids in the finite-element/finite-volume sense. In Rompy, you would typically specify:

- Horizontal grid file (hgrid.gr3): Contains node coordinates and element connectivity
- Vertical grid configuration: Defines the vertical coordinate system
- Nesting information if using nested grids

### Boundary Conditions

SCHISM supports various boundary condition types:

1. **Elevation boundaries**: Specified water surface elevation
2. **Velocity boundaries**: Specified normal velocity
3. **Flow boundaries**: Specified flow rate
4. **Tidal boundaries**: Harmonic constants for tidal constituents
5. **3D boundaries**: For temperature, salinity, and other 3D variables

```python
# Conceptual example of boundary conditions
# boundary_forcing = [
#     SCHISMTidalBoundary(
#         name="offshore_tides",
#         constituents=["M2", "S2", "K1", "O1"],
#         amplitudes=[1.2, 0.5, 0.3, 0.2],  # in meters
#         phases=[45, 90, 135, 180],         # in degrees
#     ),
#     SCHISMFlowBoundary(
#         name="river_inflow",
#         timeseries=FlowTimeseries(
#             time=[datetime(2023, 6, 1), datetime(2023, 6, 2)],
#             flow=[100, 150],  # in cms
#         ),
#     ),
#     # Add more boundary conditions as needed
# ]
```

### Physics Settings

SCHISM offers various physics options that can be configured:

- Baroclinicity: Include density-driven circulation
- Wetting and drying: Allow cells to dry and rewet
- Turbulence closure: Select vertical mixing parameterization
- Horizontal mixing: Configure lateral mixing coefficients
- Advection schemes: Choose options for tracers

### Initial Conditions

Configure the initial state of your simulation:

- Water surface elevation
- Current velocities
- Temperature and salinity fields
- Tracer concentrations

## Running SCHISM with Different Backends

### Local Execution

```python
# from rompy.backends import LocalConfig

# backend_config = LocalConfig(
#     timeout=28800,  # 8 hours
#     command="mpirun -np 16 schism -i hstime.nml",  # Adjust number of cores as needed
#     env_vars={"SCHISM_DIR": "/path/to/schism"},
# )

# success = model_run.run(backend=backend_config)
# print(f"SCHISM local execution: {'Success' if success else 'Failed'}")
```

### Docker Execution

```python
# from rompy.backends import DockerConfig

# docker_config = DockerConfig(
#     image="rompy/schism:latest",
#     timeout=57600,  # 16 hours
#     cpu=16,
#     memory="32g",
#     volumes=[f"{model_run.output_dir}:/output:rw"],
#     env_vars={"SCHISM_PARALLEL": "true"},
# )

# success = model_run.run(backend=docker_config)
# print(f"SCHISM Docker execution: {'Success' if success else 'Failed'}")
```

## Best Practices

1. **Grid Quality**: Ensure good grid quality with appropriate resolution for your application. Check for negative areas, highly skewed elements, and proper depth values.

2. **Time Stepping**: Use appropriate time steps. SCHISM is semi-implicit, allowing larger time steps, but physical processes must be properly resolved.

3. **Open Boundary Placement**: Place open boundaries where external data is available and where the model solution is less sensitive to boundary errors.

4. **Initial Conditions**: If possible, spin up the model using simpler physics before adding complexity.

5. **Validation**: Always validate your model setup against available observations before using it for prediction.

## Common Issues and Troubleshooting

### Model Crashes

- Check that the grid has no negative depths or problematic bathymetry
- Verify boundary conditions are properly specified
- Ensure time step is appropriate for the grid resolution
- Check that there are no isolated water bodies

### Incorrect Results

- Validate boundary conditions against known values
- Verify that physics options are appropriate for the study area
- Check that the model has been spun up sufficiently

### Performance Issues

- Optimize parallelization settings (number of cores)
- Consider using a barotropic mode for initial spin-up
- Tune vertical mixing parameters if needed

## Notebook Examples

For a practical, hands-on example of how to use SCHISM with Rompy, please see the following notebook:

- **[SCHISM Demo](notebooks/schism/schism_demo.ipynb)**: A basic demonstration of a SCHISM run.

## Next Steps

- Review the [Backends Guide](backends.md) for detailed execution options
- Learn about [Configuration Deep Dive](configuration_deep_dive.md) for detailed configuration options
- Check the [Progressive Tutorials](progressive_tutorials.md) for practical examples