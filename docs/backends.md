# Backend Systems

Rompy's backend system provides flexible, type-safe execution environments for ocean and coastal models. Whether you're running simple local simulations or complex containerized workflows, the backend system handles execution, resource management, and result processing.

## Overview

Backend systems in Rompy control **how** and **where** your models execute. They provide:

* **Execution Environments**: Local system, Docker containers, HPC clusters
* **Resource Management**: CPU, memory, and timeout controls
* **Type Safety**: Pydantic-based configurations with validation
* **Reproducibility**: Consistent execution across different environments
* **Scalability**: From development to production deployments

### Key Components

**Backend Configurations**
: Type-safe Pydantic models that define execution parameters. See `rompy.backends.config.BaseBackendConfig` and its subclasses.

**Run Backends**
: Execution engines that handle the actual model runs. See `rompy.run` for implementations.

**Postprocessors**
: Components that handle results after model execution. See `rompy.backends.postprocessors` for available processors.

**CLI Integration**
: Command-line tools for configuration management and execution. See [cli](cli.md) for details.

## Quick Start

Get started with backends in three simple steps:

1. **Create a Backend Configuration**

```yaml
# my_backend.yml
type: local
timeout: 3600
command: "python run_model.py"
env_vars:
  OMP_NUM_THREADS: "4"
```

2. **Validate Your Configuration**

```bash
rompy backends validate my_backend.yml
```

3. **Run Your Model**

```python
from rompy.model import ModelRun
from rompy.backends import LocalConfig

# Load and run
model = ModelRun.from_file("model_config.yml")
config = LocalConfig.from_file("my_backend.yml")
success = model.run(backend=config)
```

## Configuration Types

All backend configurations inherit from `rompy.backends.config.BaseBackendConfig` and provide type-safe, validated execution parameters.

### LocalConfig - Local System Execution

Execute models directly on your local system using `rompy.backends.config.LocalConfig`.

**Basic Usage:**

```python
from rompy.backends import LocalConfig

config = LocalConfig(
    timeout=3600,
    command="python run_simulation.py"
)
```

**Advanced Configuration:**

```yaml
# local_advanced.yml
type: local
timeout: 7200  # 2 hours
command: "python run_simulation.py --verbose"
shell: true
capture_output: true
env_vars:
  OMP_NUM_THREADS: "8"
  PYTHONPATH: "/custom/path"
  MODEL_DEBUG: "true"
```

**Key Parameters:**

* `timeout`: Maximum execution time in seconds (60-86400)
* `command`: Shell command to execute (optional)
* `shell`: Execute through shell (default: True)
* `capture_output`: Capture stdout/stderr (default: True)
* `env_vars`: Environment variables to set
* `working_dir`: Working directory for execution

For complete parameter documentation, see `rompy.backends.config.LocalConfig`.

### DockerConfig - Container Execution

Execute models inside Docker containers for reproducible, isolated environments using `rompy.backends.config.DockerConfig`.

**Basic Usage:**

```python
from rompy.backends import DockerConfig

config = DockerConfig(
    image="swan:latest",
    cpu=4,
    memory="2g",
    timeout=3600
)
```

**Advanced Configuration:**

```yaml
# docker_advanced.yml
type: docker
image: "swan:latest"
timeout: 10800  # 3 hours
cpu: 8
memory: "4g"
mpiexec: "mpirun -np 8"
user: "modeluser"
volumes:
  - "/data/input:/app/input:ro"
  - "/data/output:/app/output:rw"
env_vars:
  MODEL_THREADS: "8"
  DATA_DIR: "/app/input"
```

**Building from Dockerfile:**

```yaml
# docker_build.yml
type: docker
dockerfile: "./docker/Dockerfile"
build_context: "./docker"
build_args:
  MODEL_VERSION: "2.1.0"
cpu: 4
memory: "2g"
```

**Key Parameters:**

* `image`: Docker image to use (mutually exclusive with dockerfile)
* `dockerfile`: Path to Dockerfile to build (mutually exclusive with image)
* `cpu`: Number of CPU cores (1-128)
* `memory`: Memory limit (e.g., "2g", "512m")
* `timeout`: Maximum execution time in seconds
* `volumes`: Volume mounts in "host:container:mode" format
* `env_vars`: Environment variables to set
* `executable`: Path to executable inside container
* `mpiexec`: MPI execution command for parallel runs

For complete parameter documentation, see `rompy.backends.config.DockerConfig`.

## Using Backend Configurations

### With ModelRun

Backend configurations integrate directly with Rompy's model execution via `rompy.model.ModelRun.run`:

```python
from rompy.model import ModelRun
from rompy.backends import LocalConfig, DockerConfig

# Load your model
model_run = ModelRun.from_file("model_config.yml")

# Execute locally
local_config = LocalConfig(timeout=3600)
success = model_run.run(backend=local_config)

# Execute in Docker
docker_config = DockerConfig(
    image="rompy/swan:latest",
    cpu=4,
    memory="4g"
)
success = model_run.run(backend=docker_config)
```

### From Configuration Files

Load configurations from YAML or JSON files:

```python
import yaml
from rompy.backends import LocalConfig, DockerConfig

# Load configuration
with open("backend_config.yml") as f:
    config_data = yaml.safe_load(f)
    backend_type = config_data.pop("type")

    if backend_type == "local":
        config = LocalConfig(**config_data)
    elif backend_type == "docker":
        config = DockerConfig(**config_data)

# Use configuration
success = model_run.run(backend=config)
```

## Command Line Interface

The CLI provides comprehensive backend management capabilities. See [cli](cli.md) for complete details.

### Configuration Management

```bash
# Validate configuration
rompy backends validate my_config.yml

# List available backends
rompy backends list

# Show configuration schema
rompy backends schema --backend-type docker

# Create configuration template
rompy backends create --backend-type local --output template.yml
```

### Model Execution

```bash
# Run model with backend configuration
rompy run model_config.yml --backend-config my_backend.yml

# Run pipeline with configuration
rompy pipeline --config pipeline_config.yml
```

## Configuration Examples

### Environment-Specific Configurations

**Development Environment:**

```yaml
# dev_backend.yml
type: local
timeout: 1800  # 30 minutes
command: "python run_model.py --debug"
env_vars:
  ENV: "development"
  LOG_LEVEL: "DEBUG"
  PYTHONUNBUFFERED: "1"
```

**Production Environment:**

```yaml
# prod_backend.yml
type: docker
image: "mymodel:production"
timeout: 14400  # 4 hours
cpu: 16
memory: "32g"
mpiexec: "mpirun -np 16"
volumes:
  - "/data/production:/app/data:ro"
  - "/results/production:/app/results:rw"
env_vars:
  ENV: "production"
  LOG_LEVEL: "INFO"
```

### Resource-Based Configurations

**Small Models:**

```yaml
type: local
timeout: 3600
env_vars:
  OMP_NUM_THREADS: "4"
```

**Large Models:**

```yaml
type: docker
image: "swan:hpc"
timeout: 86400  # 24 hours
cpu: 32
memory: "64g"
mpiexec: "mpirun -np 32"
env_vars:
  OMP_NUM_THREADS: "1"
  MODEL_PRECISION: "double"
```

## Validation and Error Handling

### Type Safety

Pydantic provides comprehensive validation with clear error messages:

```python
from rompy.backends import LocalConfig, DockerConfig
from pydantic import ValidationError

try:
    # Invalid timeout (too short)
    config = LocalConfig(timeout=30)
except ValidationError as e:
    print(f"Validation error: {e}")

try:
    # Missing required image/dockerfile
    config = DockerConfig()
except ValidationError as e:
    print(f"Configuration error: {e}")
```

### Configuration Validation

Each configuration class validates fields according to execution environment requirements:

**LocalConfig Validation:**

* Working directory must exist if specified.
* Environment variables must be string key-value pairs.
* Timeout must be between 60 and 86400 seconds.

**DockerConfig Validation:**

* Either `image` or `dockerfile` must be provided (not both).
* CPU count must be between 1 and 128.
* Memory format must match pattern (e.g., "2g", "512m").
* Volume mounts must use "host:container:mode" format.
* Docker image names must follow valid naming conventions.

## Best Practices

### Configuration Management

1. **Version Control**: Keep configuration files in version control

2. **Environment Variables**: Use environment variables for sensitive data:

```python
config = LocalConfig(
    env_vars={"API_KEY": os.environ["API_KEY"]}
)
```

3. **Validation**: Always validate configurations before production use:

```bash
rompy backends validate my_config.yml
```

4. **Documentation**: Document your configurations with comments:

```yaml
# Production SWAN model configuration
type: docker
image: "swan:2.1.0"  # Pin specific version
timeout: 14400  # 4 hours for typical runs
cpu: 16  # Match server capabilities
```

### Resource Planning

1. **Start Small**: Begin with conservative resource allocations
2. **Monitor Usage**: Track actual resource consumption
3. **Scale Gradually**: Increase resources based on measured needs
4. **Set Realistic Timeouts**: Base timeouts on model complexity

### Security Considerations

1. **Container Security**: Use appropriate user permissions:

```python
config = DockerConfig(
    image="myapp:latest",
    user="appuser",  # Don't run as root
    volumes=["/data:/app/data:ro"]  # Read-only when possible
)
```

2. **Environment Variables**: Never hardcode sensitive data in configuration files

3. **Volume Mounts**: Use read-only mounts when possible

## Troubleshooting

### Common Issues

**Configuration Validation Errors**

```bash
# Check configuration syntax
rompy backends validate my_config.yml

# Show configuration schema
rompy backends schema --backend-type local
```

**Docker Issues**

```bash
# Verify Docker image exists
docker images | grep myimage

# Test Docker configuration
rompy backends validate --backend-type docker docker_config.yml
```

**Timeout Issues**

```yaml
# Increase timeout for long-running models
type: local
timeout: 21600  # 6 hours
```

**Memory Issues**

```yaml
# Increase memory allocation
type: docker
image: "swan:latest"
memory: "8g"
```

### Debugging Configuration Issues

1. **Check Validation Errors**:

```python
from pydantic import ValidationError

try:
    config = DockerConfig(**config_data)
except ValidationError as e:
    for error in e.errors():
        print(f"Field {error['loc']}: {error['msg']}")
```

2. **Verify Configuration Serialization**:

```python
config = LocalConfig(timeout=3600)
print(config.model_dump_json(indent=2))
```

3. **Test with Simple Examples**:

```python
# Start with minimal configuration
config = LocalConfig(timeout=3600)
# Add complexity gradually
```

### Getting Help

```bash
# General help
rompy backends --help

# Command-specific help
rompy backends validate --help

# Show examples
rompy backends create --backend-type local --with-examples
```

## Advanced Usage

### Custom Backend Configurations

Extend the system with custom backend types by inheriting from `rompy.backends.config.BaseBackendConfig`:

```python
from rompy.backends import BaseBackendConfig
from pydantic import Field

class HPCConfig(BaseBackendConfig):
    """Configuration for HPC cluster execution."""

    queue: str = Field(..., description="SLURM queue name")
    nodes: int = Field(1, ge=1, le=100)
    partition: str = Field("compute")

    def get_backend_class(self):
        from mypackage.backends import HPCRunBackend
        return HPCRunBackend
```

For detailed implementation guidance, see [backend_reference](developer/backend_reference.md).

### Postprocessors

Handle results after model execution using postprocessor configuration classes:

```python
from rompy.postprocess.config import NoopPostprocessorConfig

# Basic post-processing with configuration
processor_config = NoopPostprocessorConfig(validate_outputs=True)
results = model_run.postprocess(processor=processor_config)

# Custom post-processing with advanced options
processor_config = NoopPostprocessorConfig(
    validate_outputs=True,
    timeout=7200,
    env_vars={"DEBUG": "1"}
)
results = model_run.postprocess(processor=processor_config)
```

For postprocessor configuration details, see [Postprocessor Configuration](#postprocessor-configuration).

### Schema Generation

Generate configuration schemas for external tools:

```python
from rompy.backends import LocalConfig, DockerConfig
import json

# Generate JSON schema
local_schema = LocalConfig.model_json_schema()
docker_schema = DockerConfig.model_json_schema()

# Save schema for external validation
with open("local_schema.json", "w") as f:
    json.dump(local_schema, f, indent=2)
```

## Postprocessor Configuration

Postprocessors handle model output analysis and transformation using Pydantic-based configuration classes.

### Configuration Types

All postprocessor configurations inherit from `rompy.postprocess.config.BasePostprocessorConfig`.

#### NoopPostprocessorConfig - Validation Only

Validate model outputs without additional processing using `rompy.postprocess.config.NoopPostprocessorConfig`:

**Basic Usage:**

```python
from rompy.postprocess.config import NoopPostprocessorConfig

config = NoopPostprocessorConfig(
    validate_outputs=True,
    timeout=3600
)
```

**Advanced Configuration:**

```yaml
# noop_advanced.yml
type: noop
validate_outputs: true
timeout: 7200
env_vars:
  DEBUG: "1"
  LOG_LEVEL: "INFO"
working_dir: "./processing"
```

**Key Parameters:**

* `validate_outputs`: Validate model outputs before processing (default: False)
* `timeout`: Maximum processing time in seconds (60-86400)
* `env_vars`: Environment variables for processing context
* `working_dir`: Working directory for processing operations

For complete parameter documentation, see `rompy.postprocess.config.NoopPostprocessorConfig`.

### Using Postprocessor Configurations

#### With ModelRun

Postprocessor configurations integrate directly with Rompy's model execution:

```python
from rompy.model import ModelRun
from rompy.postprocess.config import NoopPostprocessorConfig

# Load your model
model_run = ModelRun.from_file("model_config.yml")

# Execute model
model_run.run(backend=backend_config)

# Post-process with configuration
processor_config = NoopPostprocessorConfig(
    validate_outputs=True,
    timeout=3600
)
results = model_run.postprocess(processor=processor_config)

if results["success"]:
    print("Post-processing completed successfully")
else:
    print(f"Post-processing failed: {results.get('error')}")
```

#### From Configuration Files

Load postprocessor configurations from YAML or JSON files:

```python
from rompy.postprocess.config import _load_processor_config

# Load configuration from file
processor_config = _load_processor_config("processor.yml")

# Use configuration
results = model_run.postprocess(processor=processor_config)
```

### Configuration File Format

Postprocessor configurations use YAML or JSON with a `type` field:

**YAML Format:**

```yaml
# Basic configuration
type: noop
validate_outputs: true
timeout: 3600

---
# Advanced configuration
type: noop
validate_outputs: true
timeout: 7200
env_vars:
  DEBUG: "1"
  LOG_LEVEL: "INFO"
  PROCESSING_MODE: "detailed"
working_dir: "./processing"
```

**JSON Format:**

```json
{
  "type": "noop",
  "validate_outputs": true,
  "timeout": 3600,
  "env_vars": {
    "DEBUG": "1"
  }
}
```

### CLI Integration

Use postprocessor configurations with CLI commands:

```bash
# Post-process existing outputs
rompy postprocess model_config.yml --processor-config processor.yml

# Run complete pipeline with postprocessor
rompy pipeline model_config.yml \
  --run-backend local \
  --processor-config processor.yml

# Validate postprocessor configuration
rompy backends validate processor.yml --processor-type noop
```

### Validation and Error Handling

#### Type Safety

Pydantic provides comprehensive validation:

```python
from rompy.postprocess.config import NoopPostprocessorConfig
from pydantic import ValidationError

try:
    # Invalid timeout (too short)
    config = NoopPostprocessorConfig(timeout=30)
except ValidationError as e:
    print(f"Validation error: {e}")

try:
    # Invalid env_vars type
    config = NoopPostprocessorConfig(env_vars=["invalid"])
except ValidationError as e:
    print(f"Configuration error: {e}")
```

#### Configuration Validation

Each configuration class validates fields according to processing requirements:

**BasePostprocessorConfig Validation:**

* `timeout` must be between 60 and 86400 seconds
* `env_vars` must be string key-value pairs
* `working_dir` must exist if specified
* `validate_outputs` must be boolean

### Custom Postprocessor Configurations

Create custom postprocessor configurations by inheriting from `BasePostprocessorConfig`:

```python
from rompy.postprocess.config import BasePostprocessorConfig
from pydantic import Field
from typing import Optional

class AnalysisPostprocessorConfig(BasePostprocessorConfig):
    """Configuration for analysis postprocessor."""
    
    type: str = Field("analysis", const=True)
    metrics: list[str] = Field(default_factory=list, description="Metrics to calculate")
    output_format: str = Field("netcdf", description="Output format")
    compress: bool = Field(True, description="Compress output files")
    plot_config: Optional[dict] = Field(None, description="Plotting configuration")
    
    def get_postprocessor_class(self):
        """Return the postprocessor class for this configuration."""
        from mypackage.postprocess import AnalysisPostprocessor
        return AnalysisPostprocessor
```

Register custom configurations in `pyproject.toml`:

```toml
[project.entry-points."rompy.postprocess.config"]
analysis = "mypackage.postprocess.config:AnalysisPostprocessorConfig"
```

### Best Practices

1. **Version Control**: Keep postprocessor configurations in version control alongside model configurations

2. **Environment Variables**: Use environment variables for environment-specific settings:

```python
import os
config = NoopPostprocessorConfig(
    env_vars={"DATA_DIR": os.environ["DATA_DIR"]}
)
```

3. **Validation**: Always validate configurations before production use:

```bash
rompy backends validate processor.yml --processor-type noop
```

4. **Documentation**: Document postprocessor configurations with comments:

```yaml
# Production post-processing configuration
type: noop
validate_outputs: true  # Ensure all expected outputs exist
timeout: 7200  # 2 hours for large model outputs
env_vars:
  DEBUG: "0"  # Disable debug mode in production
```

### Schema Generation

Generate configuration schemas for validation and documentation:

```python
from rompy.postprocess.config import NoopPostprocessorConfig
import json

# Generate JSON schema
schema = NoopPostprocessorConfig.model_json_schema()

# Save for external validation
with open("noop_schema.json", "w") as f:
    json.dump(schema, f, indent=2)
```

## Integration Examples

### Complete Workflow Example

```python
from rompy.model import ModelRun
from rompy.backends import DockerConfig

# Load model
model = ModelRun.from_file("swan_model.yml")

# Configure backend
backend = DockerConfig(
    image="swan:latest",
    cpu=8,
    memory="8g",
    timeout=7200,
    volumes=[
        "/data/bathymetry:/app/bathy:ro",
        "/data/forcing:/app/forcing:ro",
        "/results:/app/results:rw"
    ]
)

# Execute
success = model.run(backend=backend)

if success:
    print("Model execution completed successfully")
else:
    print("Model execution failed")
```

### Pipeline Integration

```python
from rompy.pipeline import LocalPipelineBackend
from rompy.backends import LocalConfig, DockerConfig
from rompy.postprocess.config import NoopPostprocessorConfig

# Create pipeline with different backends for different stages
backend = LocalPipelineBackend()

# Configure run backend
run_config = DockerConfig(
    image="swan:latest",
    cpu=16,
    memory="32g",
    timeout=14400
)

# Configure postprocessor
processor_config = NoopPostprocessorConfig(
    validate_outputs=True,
    timeout=3600
)

# Execute pipeline
results = backend.execute(
    model_run=model_run,
    run_backend=run_config,
    processor_config=processor_config,
    cleanup_on_failure=False
)

if results["success"]:
    print(f"Pipeline completed. Stages: {results['stages_completed']}")
else:
    print(f"Pipeline failed at stage: {results['stages_completed'][-1]}")
```

## Notebook Examples

For a practical, hands-on example of how to use the different backends, please see the following notebook:

- **[Backend Examples](notebooks/backends/backend_examples.ipynb)**: A demonstration of how to use the local and Docker backends.

## API Reference


For complete API documentation, see:

* `rompy.backends.config.BaseBackendConfig` - Base configuration class
* `rompy.backends.config.LocalConfig` - Local execution configuration
* `rompy.backends.config.DockerConfig` - Docker execution configuration
* `rompy.postprocess.config.BasePostprocessorConfig` - Base postprocessor configuration
* `rompy.postprocess.config.NoopPostprocessorConfig` - No-op postprocessor configuration
* `rompy.run` - Run backend implementations
* `rompy.postprocess` - Postprocessor implementations
* [backend_reference](developer/backend_reference.md) - Comprehensive technical reference

The backend system provides a robust, type-safe foundation for model execution while maintaining flexibility for different deployment scenarios. From simple local development to complex containerized production environments, the backend system adapts to your needs while ensuring consistent, reproducible results.