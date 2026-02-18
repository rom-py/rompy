# Plugin Architecture

Rompy features a flexible plugin-based architecture that allows for extensible model execution and output processing. The system uses Python entry points to automatically discover and load plugins, making it easy to extend with custom implementations.

## Core Plugin Categories

ROMPY implements three main plugin categories using Python entry points:

1.  **Configuration Plugins (`rompy.config`)**: Model-specific configurations.
2.  **Data Source Plugins (`rompy.source`)**: Custom data acquisition implementations.
3.  **Execution Plugins**: Three subcategories:
    - **Run Backends (`rompy.run`)**: Model execution environments.
    - **Postprocessors (`rompy.postprocess`)**: Output analysis and transformation implementations.
    - **Postprocessor Configurations (`rompy.postprocess.config`)**: Pydantic-based postprocessor configurations.
    - **Pipeline Backends (`rompy.pipeline`)**: Workflow orchestration.

## Dual Selection Pattern

ROMPY uses two distinct selection patterns for different plugin types:

-   **Pattern 1: Pydantic Discriminated Union (for configurations)**
    -   **Selection**: At model instantiation time via a `model_type` discriminator field.
    -   **State**: The configuration becomes part of the persistent, serializable model state.
    -   **Benefit**: Enables reproducible science with full validation.

-   **Pattern 2: Runtime String Selection (for backends)**
    -   **Selection**: At execution time via string parameters.
    -   **State**: Allows environment-specific deployment without changing the model configuration.
    -   **Benefit**: Supports late binding and optional availability.

## Entry Point Registration

All plugins are registered in `pyproject.toml`:

```toml
[project.entry-points."rompy.config"]
swan = "rompy.swan.config:SwanConfig"
schism = "rompy.schism.config:SCHISMConfig"

[project.entry-points."rompy.source"]
file = "rompy.core.source:SourceFile"
intake = "rompy.core.source:SourceIntake"

[project.entry-points."rompy.run"]
local = "rompy.run:LocalRunBackend"
docker = "rompy.run.docker:DockerRunBackend"

[project.entry-points."rompy.postprocess.config"]
noop = "rompy.postprocess.config:NoopPostprocessorConfig"
```

For basic plugin usage, please see the [Getting Started Guide](getting_started.md) and [Advanced Topics](backends.md).


## Run Backends

Run backends are responsible for executing models in different environments. They all implement a common interface with a `run()` method.

### Built-in Run Backends

#### Local Backend

The `local` backend executes models directly on the local system:

```python
# Basic local execution
success = model.run(backend="local")

# With custom command
success = model.run(
    backend="local",
    command="./my_model_executable",
    env_vars={"OMP_NUM_THREADS": "4"},
    timeout=3600
)
```

#### Docker Backend

The `docker` backend executes models inside Docker containers:

```python
# Using pre-built image
success = model.run(
    backend="docker",
    image="rompy/schism:latest",
    executable="/usr/local/bin/schism",
    cpu=4,
    volumes=["./data:/data:ro"],
    env_vars={"MODEL_CONFIG": "production"}
)

# Building from Dockerfile
success = model.run(
    backend="docker",
    dockerfile="./docker/Dockerfile",
    build_args={"MODEL_VERSION": "1.0.0"},
    executable="/usr/local/bin/model",
    mpiexec="mpiexec",
    cpu=8
)
```

### Custom Run Backends

You can create custom run backends by implementing the run interface:

```python
class CustomRunBackend:
    """Custom run backend example."""

    def run(self, model_run, **kwargs):
        """Execute the model run.

        Args:
            model_run: The ModelRun instance
            **kwargs: Backend-specific parameters

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Generate model inputs
            model_run.generate()

            # Custom execution logic here
            return self._execute_custom_logic(model_run, **kwargs)

        except Exception as e:
            logger.exception(f"Custom backend failed: {e}")
            return False
```

Register custom backends via entry points in `pyproject.toml`:

```toml
[project.entry-points."rompy.run"]
custom = "mypackage.backends:CustomRunBackend"
```

## Postprocessors

Postprocessors handle analysis and transformation of model outputs. They use Pydantic configuration classes for type-safe parameter handling.

### Postprocessor Configuration

All postprocessor configurations inherit from `BasePostprocessorConfig` and are registered via entry points:

```toml
[project.entry-points."rompy.postprocess.config"]
noop = "rompy.postprocess.config:NoopPostprocessorConfig"
analysis = "mypackage.config:AnalysisPostprocessorConfig"
```

### Built-in Postprocessor Configurations

#### No-op Processor Configuration

The `noop` processor provides basic validation without processing:

```python
from rompy.postprocess.config import NoopPostprocessorConfig

# Basic validation
config = NoopPostprocessorConfig(validate_outputs=True)
results = model.postprocess(processor=config)

# With custom configuration
config = NoopPostprocessorConfig(
    validate_outputs=True,
    timeout=3600,
    env_vars={"DEBUG": "1"}
)
results = model.postprocess(processor=config)
```

**From Configuration File:**

```yaml
# processor.yml
type: noop
validate_outputs: true
timeout: 3600
env_vars:
  DEBUG: "1"
  LOG_LEVEL: "INFO"
```

```python
from rompy.postprocess.config import _load_processor_config

# Load from file
config = _load_processor_config("processor.yml")
results = model.postprocess(processor=config)
```

### Custom Postprocessor Configurations

Create custom postprocessor configurations by inheriting from `BasePostprocessorConfig`:

```python
from rompy.postprocess.config import BasePostprocessorConfig
from pydantic import Field
from typing import Optional

class AnalysisPostprocessorConfig(BasePostprocessorConfig):
    """Configuration for analysis postprocessor."""
    
    type: str = Field("analysis", const=True)
    metrics: list[str] = Field(
        default_factory=list,
        description="Metrics to calculate"
    )
    output_format: str = Field(
        "netcdf",
        description="Output format for results"
    )
    compress: bool = Field(
        True,
        description="Compress output files"
    )
    plot_config: Optional[dict] = Field(
        None,
        description="Configuration for plotting"
    )
    
    def get_postprocessor_class(self):
        """Return the postprocessor implementation class."""
        from mypackage.postprocess import AnalysisPostprocessor
        return AnalysisPostprocessor
```

### Custom Postprocessor Implementation

Create the postprocessor implementation class:

```python
from pathlib import Path
from typing import Dict, Any

class AnalysisPostprocessor:
    """Custom postprocessor for model analysis."""

    def process(self, model_run, config: AnalysisPostprocessorConfig, **kwargs) -> Dict[str, Any]:
        """Process model outputs with configuration.

        Args:
            model_run: The ModelRun instance
            config: The AnalysisPostprocessorConfig instance
            **kwargs: Additional processor-specific parameters

        Returns:
            dict: Processing results with success status
        """
        try:
            output_dir = Path(model_run.output_dir) / model_run.run_id

            # Use configuration parameters
            metrics = self._calculate_metrics(
                output_dir,
                metrics=config.metrics,
                output_format=config.output_format
            )
            
            if config.plot_config:
                plots = self._generate_plots(output_dir, config.plot_config)
            else:
                plots = []
            
            # Optionally compress outputs
            if config.compress:
                self._compress_outputs(output_dir)

            return {
                "success": True,
                "metrics": metrics,
                "plots": plots,
                "compressed": config.compress,
                "message": "Analysis completed successfully"
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Analysis failed: {e}"
            }

    def _calculate_metrics(self, output_dir, metrics, output_format):
        """Calculate requested metrics."""
        # Implementation details
        pass

    def _generate_plots(self, output_dir, plot_config):
        """Generate plots based on configuration."""
        # Implementation details
        pass

    def _compress_outputs(self, output_dir):
        """Compress output files."""
        # Implementation details
        pass
```

Register via entry points in `pyproject.toml`:

```toml
[project.entry-points."rompy.postprocess.config"]
analysis = "mypackage.postprocess.config:AnalysisPostprocessorConfig"

[project.entry-points."rompy.postprocess"]
analysis = "mypackage.postprocess:AnalysisPostprocessor"
```

### Usage Example

```python
from mypackage.postprocess.config import AnalysisPostprocessorConfig

# Create configuration
config = AnalysisPostprocessorConfig(
    validate_outputs=True,
    metrics=["mean", "variance", "peak"],
    output_format="netcdf",
    compress=True,
    plot_config={
        "figsize": (10, 8),
        "dpi": 300
    }
)

# Use in model workflow
model = ModelRun.from_file("model.yml")
model.run(backend=backend_config)
results = model.postprocess(processor=config)

if results["success"]:
    print(f"Calculated metrics: {results['metrics']}")
    print(f"Generated plots: {results['plots']}")
```

**CLI Usage:**

```yaml
# analysis_processor.yml
type: analysis
validate_outputs: true
metrics:
  - mean
  - variance
  - peak
output_format: netcdf
compress: true
plot_config:
  figsize: [10, 8]
  dpi: 300
```

```bash
rompy postprocess model.yml --processor-config analysis_processor.yml
```

## Pipeline Backends

Pipeline backends orchestrate the complete model workflow from input generation through execution to output processing.

### Built-in Pipeline Backends

#### Local Pipeline

The `local` pipeline executes all stages locally:

```python
from rompy.postprocess.config import NoopPostprocessorConfig

# Basic pipeline
results = model.pipeline(pipeline_backend="local")

# With custom configurations
processor_config = NoopPostprocessorConfig(
    validate_outputs=True,
    timeout=3600
)

results = model.pipeline(
    pipeline_backend="local",
    run_backend="docker",
    processor_config=processor_config,
    run_kwargs={"image": "rompy/model:latest", "cpu": 4},
    cleanup_on_failure=True
)
```

### Custom Pipeline Backends

Create custom pipeline backends for distributed or cloud execution:

```python
class CloudPipelineBackend:
    """Pipeline backend for cloud execution."""

    def execute(self, model_run, run_backend, processor_config, **kwargs):
        """Execute the complete pipeline.

        Args:
            model_run: The ModelRun instance
            run_backend: Backend configuration for model execution
            processor_config: BasePostprocessorConfig instance for postprocessing
            **kwargs: Pipeline-specific parameters

        Returns:
            dict: Pipeline execution results
        """
        results = {
            "success": False,
            "run_id": model_run.run_id,
            "stages_completed": []
        }

        try:
            # Stage 1: Generate inputs
            model_run.generate()
            results["stages_completed"].append("generate")

            # Stage 2: Submit to cloud
            job_id = self._submit_cloud_job(model_run, run_backend, **kwargs)
            results["job_id"] = job_id
            results["stages_completed"].append("submit")

            # Stage 3: Wait for completion
            self._wait_for_completion(job_id)
            results["stages_completed"].append("execute")

            # Stage 4: Download and process results with configuration
            outputs = self._download_results(job_id)
            processed = self._process_outputs(outputs, processor_config)
            results["outputs"] = processed
            results["stages_completed"].append("postprocess")

            results["success"] = True
            return results

        except Exception as e:
            results["error"] = str(e)
            return results
```

## Best Practices

### Error Handling

- Always wrap main logic in try-catch blocks
- Return appropriate boolean/dict responses
- Log errors with sufficient detail for debugging
- Clean up resources on failure when possible

### Parameter Validation

- Validate required parameters early
- Provide clear error messages for invalid inputs
- Use type hints for better IDE support
- Document all parameters in docstrings

### Logging

- Use structured logging with appropriate levels
- Include run_id and context in log messages
- Log progress for long-running operations
- Avoid logging sensitive information

### Resource Management

- Clean up temporary files and directories
- Handle timeouts gracefully
- Implement proper cancellation mechanisms
- Monitor resource usage for long-running processes

### Testing

- Write unit tests for all backend methods
- Mock external dependencies (Docker, cloud APIs)
- Test error conditions and edge cases
- Include integration tests where appropriate

## API Reference

::: rompy.run
::: rompy.postprocess
::: rompy.pipeline

## Next Steps

- Review the [Architecture Overview](architecture_overview.md) for more details on the overall system design
- Check the [Developer Guide](developer/index.md) for advanced development topics
- Look at the [API Reference](api.md) for detailed class documentation