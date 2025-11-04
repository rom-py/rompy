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


## Using YAML Configuration Files

One of the key advantages of Rompy's schema-based approach is the ability to represent complex model configurations as transportable YAML files. This section demonstrates how to convert Python-based configurations to YAML and run them using Rompy's command-line interface.

### Converting Python Configuration to YAML

Let's take the complete workflow example from Tutorial 6 and represent it as a YAML configuration file:

```yaml
# model_config.yaml
run_id: "yaml_workflow"
period:
  start: "2023-01-01T00:00:00"
  end: "2023-01-02T00:00:00"
  interval: "1H"
config:
  template: "path/to/template"
  checkout: "path/to/checkout"
  grid:
    _type: "regular"
    lon_min: -75.0
    lon_max: -65.0
    lat_min: 35.0
    lat_max: 45.0
    dx: 0.1
    dy: 0.1
output_dir: "./yaml_output"
```

### Understanding the YAML Structure

The YAML representation preserves all the information from the Python configuration:

1. **Discriminator Field**: The `_type: "regular"` field identifies the specific grid implementation
2. **Hierarchical Structure**: Nested objects maintain the same structure as in Python
3. **Type Safety**: The schema ensures all values match expected types when loaded
4. **Validation**: All constraints defined in the Pydantic models are enforced

### Running with the Command Line Interface

Once you have your YAML configuration, you can run it using Rompy's CLI:

```bash
rompy run --config model_config.yaml
```

To specify a different backend:

```bash
rompy run --config model_config.yaml --backend local --timeout 3600
```

For more information about available CLI options, see the [CLI Reference](cli.md).

### Benefits of YAML Configuration

1. **Transportability**: The entire model configuration is contained in a single, human-readable file
2. **Version Control**: YAML files can be easily committed to version control systems
3. **Reproducibility**: Sharing a single YAML file allows others to reproduce the exact same model run
4. **Declarative**: The config file fully describes the model run without requiring Python code
5. **Validation**: All configurations are validated against the schema when loaded

### Converting an Existing Python Configuration to YAML

You can programmatically generate YAML from a Python configuration:

```python
from rompy.model import ModelRun
from rompy.core.config import BaseConfig
from rompy.core.time import TimeRange
from rompy.core.grid import RegularGrid
from datetime import datetime

# Create your configuration in Python
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

config = BaseConfig(
    template="path/to/template",
    checkout="path/to/checkout",
    grid=grid,
)

model_run = ModelRun(
    run_id="yaml_export",
    period=time_range,
    config=config,
    output_dir="./yaml_export_output",
)

# Export the configuration to YAML
yaml_content = model_run.model_dump_yaml()
print(yaml_content)

# Or save directly to a file
with open("exported_config.yaml", "w") as f:
    f.write(yaml_content)
```

### Loading and Using YAML Configuration

To use a YAML configuration in Python:

```python
from rompy.model import ModelRun

# Load the configuration from YAML
with open("model_config.yaml", "r") as f:
    yaml_content = f.read()

# Create the model run from YAML
model_run = ModelRun.model_validate_yaml(yaml_content)

# Now run as normal
staging_dir = model_run.generate()
print(f"Generated at: {staging_dir}")

# Execute with a backend
backend_config = LocalConfig(timeout=3600, command="your_model_executable")
success = model_run.run(backend=backend_config)
print(f"Execution status: {'Success' if success else 'Failed'}")
```

This approach allows for maximum flexibility - you can create configurations in Python, export them to YAML for sharing, and load them back into Python when needed, all while maintaining the validation benefits of the schema-driven approach.
```

## Model-Specific Tutorials

For model-specific tutorials on SWAN, SCHISM, and other supported models, see the [Model Guides](models.md).

## Next Steps

- Explore [Configuration Deep Dive](configuration_deep_dive.md) for detailed configuration options
- Learn about [Common Workflows](common_workflows.md) for best practices
- Check out the [Advanced Topics](backends.md) for more complex usage
- Review the [API Reference](api.md) for comprehensive documentation of all classes and methods