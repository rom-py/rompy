# Plugin Architecture

Rompy features a flexible plugin-based architecture that allows for extensible model execution and output processing. The system uses Python entry points to automatically discover and load plugins, making it easy to extend with custom implementations.

## Core Plugin Categories

ROMPY implements three main plugin categories using Python entry points:

1.  **Configuration Plugins (`rompy.config`)**: Model-specific configurations.
2.  **Data Source Plugins (`rompy.source`)**: Custom data acquisition implementations.
3.  **Execution Plugins**: Three subcategories:
    - **Run Backends (`rompy.run`)**: Model execution environments.
    - **Postprocessors (`rompy.postprocess`)**: Output analysis and transformation.
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

Postprocessors handle analysis and transformation of model outputs. They implement a `process()` method that returns a dictionary with results.

### Built-in Postprocessors

#### No-op Processor

The `noop` processor provides basic validation without processing:

```python
# Basic validation
results = model.postprocess(processor="noop")

# With custom validation
results = model.postprocess(
    processor="noop",
    validate_outputs=True,
    output_dir="./custom_output"
)
```

### Custom Postprocessors

Create custom postprocessors by implementing the process interface:

```python
class AnalysisPostprocessor:
    """Custom postprocessor for model analysis."""

    def process(self, model_run, **kwargs):
        """Process model outputs.

        Args:
            model_run: The ModelRun instance
            **kwargs: Processor-specific parameters

        Returns:
            dict: Processing results
        """
        try:
            output_dir = Path(model_run.output_dir) / model_run.run_id

            # Custom analysis logic
            metrics = self._calculate_metrics(output_dir)
            plots = self._generate_plots(output_dir)

            return {
                "success": True,
                "metrics": metrics,
                "plots": plots,
                "message": "Analysis completed successfully"
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Analysis failed: {e}"
            }
```

Register via entry points:

```toml
[project.entry-points."rompy.postprocess"]
analysis = "mypackage.processors:AnalysisPostprocessor"
```

## Pipeline Backends

Pipeline backends orchestrate the complete model workflow from input generation through execution to output processing.

### Built-in Pipeline Backends

#### Local Pipeline

The `local` pipeline executes all stages locally:

```python
# Basic pipeline
results = model.pipeline(pipeline_backend="local")

# With custom backends
results = model.pipeline(
    pipeline_backend="local",
    run_backend="docker",
    processor="analysis",
    run_kwargs={"image": "rompy/model:latest", "cpu": 4},
    process_kwargs={"create_plots": True},
    cleanup_on_failure=True
)
```

### Custom Pipeline Backends

Create custom pipeline backends for distributed or cloud execution:

```python
class CloudPipelineBackend:
    """Pipeline backend for cloud execution."""

    def execute(self, model_run, **kwargs):
        """Execute the complete pipeline.

        Args:
            model_run: The ModelRun instance
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
            job_id = self._submit_cloud_job(model_run, **kwargs)
            results["job_id"] = job_id
            results["stages_completed"].append("submit")

            # Stage 3: Wait for completion
            self._wait_for_completion(job_id)
            results["stages_completed"].append("execute")

            # Stage 4: Download and process results
            outputs = self._download_results(job_id)
            processed = self._process_outputs(outputs, **kwargs)
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