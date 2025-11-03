# Progressive Tutorials

This section contains a series of progressive tutorials that gradually introduce more complex concepts. Each tutorial builds on the previous one, creating a learning path from basic usage to advanced features. If you're new to Rompy, you may want to start with the [User Guide](user_guide.md).

## Tutorial 1: Basic Model Configuration and Execution

In this first tutorial, we'll cover the fundamentals of creating a model configuration and running it.

```python
from rompy.model import ModelRun
from rompy.core.config import BaseConfig
from rompy.core.time import TimeRange
from datetime import datetime

# Define a simple model configuration
config = BaseConfig(
    template="path/to/template",
    checkout="path/to/checkout",
)

# Define the time period for the simulation
time_range = TimeRange(
    start=datetime(2023, 1, 1),
    end=datetime(2023, 1, 2),
    interval="1H",
)

# Create a model run
model_run = ModelRun(
    run_id="basic_tutorial",
    period=time_range,
    config=config,
    output_dir="./output",
)

# Generate the model input files
staging_dir = model_run.generate()
print(f"Model files generated at: {staging_dir}")
```

## Tutorial 2: Adding a Grid Configuration

Let's extend the basic example by adding a grid configuration:

```python
from rompy.core.grid import RegularGrid

# Define a regular grid
grid = RegularGrid(
    lon_min=-75.0,
    lon_max=-65.0,
    lat_min=35.0,
    lat_max=45.0,
    dx=0.1,
    dy=0.1,
)

# Create a configuration with the grid
config_with_grid = BaseConfig(
    template="path/to/template",
    checkout="path/to/checkout",
    grid=grid,  # Add the grid configuration
)

# Create and run the model as before
model_run = ModelRun(
    run_id="grid_tutorial",
    period=time_range,
    config=config_with_grid,
    output_dir="./output_grid",
)

staging_dir = model_run.generate()
print(f"Model with grid config generated at: {staging_dir}")
```

## Tutorial 3: Using Data Sources

Now, let's add data sources to our configuration:

```python
from rompy.core.data import DataGrid
from rompy.core.source import SourceFile

# Define a data source
data_source = SourceFile(
    uri="path/to/data.nc",
    driver="netcdf",
)

# Create a data object using the source
data_object = DataGrid(
    source=data_source,
    var_map={"significant_wave_height": "swh"},
)

# Create a configuration with grid and data
config_with_data = BaseConfig(
    template="path/to/template",
    checkout="path/to/checkout",
    grid=grid,
    # Add data sources to the configuration
    data_sources=[data_object],
)

model_run = ModelRun(
    run_id="data_tutorial",
    period=time_range,
    config=config_with_data,
    output_dir="./output_data",
)

staging_dir = model_run.generate()
print(f"Model with data sources generated at: {staging_dir}")
```

## Tutorial 4: Multi-Source Data Integration

Let's see how to integrate multiple data sources:

```python
from rompy.core.source import SourceIntake

# Define additional data sources
remote_source = SourceIntake(
    catalog="https://catalog.example.com/catalog.yml",
    entry="ocean_currents",
)

# Create multiple data objects
wave_data = DataGrid(
    source=data_source,  # From previous tutorial
    var_map={"significant_wave_height": "swh"},
)

current_data = DataGrid(
    source=remote_source,
    var_map={"eastward_sea_water_velocity": "u", "northward_sea_water_velocity": "v"},
)

# Create configuration with multiple data sources
config_multi_data = BaseConfig(
    template="path/to/template",
    checkout="path/to/checkout",
    grid=grid,
    data_sources=[wave_data, current_data],
)

model_run = ModelRun(
    run_id="multi_data_tutorial",
    period=time_range,
    config=config_multi_data,
    output_dir="./output_multi_data",
)

staging_dir = model_run.generate()
print(f"Model with multiple data sources generated at: {staging_dir}")
```

## Tutorial 5: Model Execution with Different Backends

Now let's run our model using different execution backends:

```python
from rompy.backends import LocalConfig, DockerConfig

# Execute with local backend
local_config = LocalConfig(
    timeout=3600,
    command="your_model_executable",
    env_vars={"OMP_NUM_THREADS": "4"},
)

# Run the model
success_local = model_run.run(backend=local_config)
print(f"Local execution status: {'Success' if success_local else 'Failed'}")

# Execute with Docker backend (conceptual)
docker_config = DockerConfig(
    image="model_image:latest",
    timeout=7200,
    cpu=4,
    memory="8g",
    volumes=[f"{model_run.output_dir}:/output:rw"],
)

# Run the model in Docker
success_docker = model_run.run(backend=docker_config)
print(f"Docker execution status: {'Success' if success_docker else 'Failed'}")
```

## Tutorial 6: Post-processing Results

Finally, let's process the results after model execution:

```python
# Process results after successful execution
if success_local:
    # Use a basic processor
    results = model_run.postprocess(processor="noop")
    print(f"Post-processing results: {results}")
    
    # Or run a complete pipeline (generate, run, and process)
    pipeline_results = model_run.pipeline(
        pipeline_backend="local",
        run_backend="local",
        processor="noop",
        run_kwargs={"timeout": 3600, "command": "your_model_executable"},
        process_kwargs={"cleanup": True},
    )
    print(f"Pipeline results: {pipeline_results}")
```

## Advanced Tutorial: Complete Workflow with Error Handling

For a more complete example with error handling and validation:

```python
from rompy.model import ModelRun
from rompy.core.config import BaseConfig
from rompy.core.time import TimeRange
from rompy.core.grid import RegularGrid
from rompy.backends import LocalConfig
from datetime import datetime

def run_complete_model_workflow():
    try:
        # 1. Define spatial and temporal domain
        grid = RegularGrid(
            lon_min=-75.0,
            lon_max=-65.0,
            lat_min=35.0,
            lat_max=45.0,
            dx=0.1,
            dy=0.1,
        )
        
        time_range = TimeRange(
            start=datetime(2023, 1, 1),
            end=datetime(2023, 1, 2),
            interval="1H"
        )
        
        # 2. Create configuration
        config = BaseConfig(
            template="path/to/template",
            checkout="path/to/checkout",
            grid=grid,
        )
        
        # 3. Create model run
        model_run = ModelRun(
            run_id="complete_workflow",
            period=time_range,
            config=config,
            output_dir="./complete_output",
        )
        
        # 4. Generate inputs
        print("Generating model input files...")
        staging_dir = model_run.generate()
        print(f"Input files generated at: {staging_dir}")
        
        # 5. Execute model
        print("Executing model run...")
        backend_config = LocalConfig(
            timeout=3600,
            command="your_model_executable"  # Replace with actual command
        )
        
        success = model_run.run(backend=backend_config)
        
        if success:
            print("Model execution completed successfully!")
            
            # 6. Process results
            print("Processing results...")
            results = model_run.postprocess(processor="noop")
            print(f"Post-processing results: {results}")
            
            return {"success": True, "results": results}
        else:
            print("Model execution failed!")
            return {"success": False, "error": "Model execution failed"}
            
    except Exception as e:
        print(f"Workflow failed with error: {str(e)}")
        return {"success": False, "error": str(e)}

# Run the complete workflow
workflow_result = run_complete_model_workflow()
print(f"Workflow result: {workflow_result}")
```

## Model-Specific Tutorials

For model-specific tutorials on SWAN, SCHISM, and other supported models, see the [Model Guides](models.md).

## Next Steps

- Explore [Configuration Deep Dive](configuration_deep_dive.md) for detailed configuration options
- Learn about [Common Workflows](common_workflows.md) for best practices
- Check out the [Advanced Topics](backends.md) for more complex usage
- Review the [API Reference](api.md) for comprehensive documentation of all classes and methods