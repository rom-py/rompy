# Backend Reference

This document provides comprehensive technical reference for Rompy's backend system, focusing on concepts, usage patterns, and advanced configuration techniques.

> [!NOTE]
> For getting started with backends, see [backends](https://rom-py.github.io/rompy/backends/). For complete API documentation, see [api](../api.md).

## Backend Configuration System

The backend system uses Pydantic models to provide type-safe, validated execution parameters. All configurations inherit from `rompy.backends.config.BaseBackendConfig`.

### Configuration Hierarchy

```
BaseBackendConfig
├── LocalConfig          # Local system execution
├── DockerConfig         # Docker container execution
└── CustomConfig         # User-defined configurations
```

### Configuration Loading

Configurations can be loaded from files or created programmatically:

```python
import yaml
from rompy.backends import LocalConfig, DockerConfig

# From YAML file
with open("config.yml") as f:
    config_data = yaml.safe_load(f)
    config = LocalConfig(**config_data)

# Programmatically
config = DockerConfig(
    image="swan:latest",
    cpu=4,
    memory="2g"
)
```

For complete configuration class documentation, see:

* `rompy.backends.config.BaseBackendConfig`
* `rompy.backends.config.LocalConfig`
* `rompy.backends.config.DockerConfig`

## Configuration File Formats

Backend configurations support YAML and JSON formats with a common structure.

### YAML Format

```yaml
# Local execution example
type: local
timeout: 3600
command: "python run_model.py"
env_vars:
  OMP_NUM_THREADS: "4"
  MODEL_DEBUG: "true"

---
# Docker execution example
type: docker
image: "swan:latest"
cpu: 8
memory: "4g"
timeout: 10800
volumes:
  - "/data/input:/app/input:ro"
  - "/data/output:/app/output:rw"
env_vars:
  MODEL_THREADS: "8"
```

### JSON Format

```json
{
  "type": "local",
  "timeout": 3600,
  "command": "python run_model.py",
  "env_vars": {
    "OMP_NUM_THREADS": "4"
  }
}
```

## Configuration Validation

Pydantic provides comprehensive validation with descriptive error messages.

### Validation Rules

**Common Validation (BaseBackendConfig):**

* `timeout`: Must be between 60 and 86400 seconds
* `env_vars`: Must be string key-value pairs
* `working_dir`: Must exist if specified

**LocalConfig Validation:**

* `command`: Must be non-empty string if provided
* `shell`: Must be boolean
* `capture_output`: Must be boolean

**DockerConfig Validation:**

* Either `image` or `dockerfile` must be provided (not both)
* `cpu`: Must be between 1 and 128
* `memory`: Must match pattern (e.g., "2g", "512m")
* `volumes`: Must use "host:container[:mode]" format with existing host paths

### Error Handling

```python
from rompy.backends import DockerConfig
from pydantic import ValidationError

try:
    config = DockerConfig(cpu=200)  # Invalid - exceeds maximum
except ValidationError as e:
    for error in e.errors():
        print(f"Field {error['loc']}: {error['msg']}")
```

## Schema Generation

Generate configuration schemas for validation and documentation:

```python
from rompy.backends import LocalConfig
import json

# Generate JSON schema
schema = LocalConfig.model_json_schema()

# Save for external validation
with open("local_schema.json", "w") as f:
    json.dump(schema, f, indent=2)
```

### Using Schemas

```python
import jsonschema

# Validate configuration data against schema
config_data = {"timeout": 3600, "command": "python run.py"}
schema = LocalConfig.model_json_schema()

try:
    jsonschema.validate(config_data, schema)
    print("Configuration is valid")
except jsonschema.ValidationError as e:
    print(f"Validation error: {e.message}")
```

## Advanced Configuration Patterns

### Dynamic Configuration

Create configurations based on runtime conditions:

```python
import psutil
from rompy.backends import LocalConfig, DockerConfig

def create_optimal_config():
    """Create configuration based on system resources."""
    cpu_count = psutil.cpu_count()
    memory_gb = psutil.virtual_memory().total // (1024**3)

    if memory_gb > 16 and cpu_count > 8:
        return DockerConfig(
            image="swan:hpc",
            cpu=cpu_count,
            memory=f"{memory_gb}g",
            mpiexec=f"mpirun -np {cpu_count}"
        )
    else:
        return LocalConfig(
            timeout=7200,
            env_vars={"OMP_NUM_THREADS": str(min(cpu_count, 4))}
        )
```

### Environment-Based Configuration

Load different configurations based on environment:

```python
import os
from rompy.backends import LocalConfig, DockerConfig

def load_config_for_environment():
    """Load configuration based on ROMPY_ENV environment variable."""
    env = os.getenv("ROMPY_ENV", "development")

    configs = {
        "production": DockerConfig(
            image="swan:production",
            cpu=16,
            memory="32g",
            timeout=21600
        ),
        "staging": DockerConfig(
            image="swan:staging",
            cpu=8,
            memory="16g",
            timeout=10800
        ),
        "development": LocalConfig(
            timeout=3600,
            env_vars={"LOG_LEVEL": "DEBUG"}
        )
    }

    return configs.get(env, configs["development"])
```

### Configuration Templates

Create reusable configuration templates:

```python
from rompy.backends import DockerConfig

# Base template
BASE_SWAN_CONFIG = {
    "image": "swan:latest",
    "user": "modeluser",
    "timeout": 7200,
    "env_vars": {
        "MODEL_DEBUG": "false",
        "LOG_LEVEL": "INFO"
    }
}

# Specialized configurations
def create_hpc_config(**overrides):
    """Create HPC-optimized configuration."""
    config_data = {
        **BASE_SWAN_CONFIG,
        "cpu": 32,
        "memory": "64g",
        "mpiexec": "mpirun -np 32",
        **overrides
    }
    return DockerConfig(**config_data)

def create_dev_config(**overrides):
    """Create development configuration."""
    config_data = {
        **BASE_SWAN_CONFIG,
        "cpu": 2,
        "memory": "2g",
        "remove_container": False,  # Keep for debugging
        "env_vars": {
            **BASE_SWAN_CONFIG["env_vars"],
            "MODEL_DEBUG": "true",
            "LOG_LEVEL": "DEBUG"
        },
        **overrides
    }
    return DockerConfig(**config_data)
```

## Creating Custom Backends

The backend system supports custom implementations through inheritance and entry points.

### Custom Configuration Classes

Create custom configuration classes by inheriting from `rompy.backends.config.BaseBackendConfig`:

```python
from rompy.backends.config import BaseBackendConfig
from pydantic import Field, validator
from typing import Optional

class SlurmConfig(BaseBackendConfig):
    """Configuration for SLURM cluster execution."""

    queue: str = Field(..., description="SLURM queue name")
    nodes: int = Field(1, ge=1, le=100, description="Number of nodes")
    partition: str = Field("compute", description="Cluster partition")
    time_limit: str = Field("1:00:00", description="Time limit (HH:MM:SS)")
    account: Optional[str] = Field(None, description="Account for billing")

    @validator('time_limit')
    def validate_time_limit(cls, v):
        import re
        if not re.match(r'^\d{1,2}:\d{2}:\d{2}$', v):
            raise ValueError("Time limit must be in format HH:MM:SS")
        return v

    def get_backend_class(self):
        from mypackage.backends import SlurmRunBackend
        return SlurmRunBackend
```

### Custom Backend Implementation

Implement backend classes that work with your custom configurations:

```python
import logging
from pathlib import Path

class SlurmRunBackend:
    """Execute models on SLURM clusters."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def run(self, model_run, config: SlurmConfig) -> bool:
        """Submit model run to SLURM queue."""
        try:
            # Generate model input files
            model_run.generate()

            # Create and submit SLURM job
            job_script = self._create_job_script(model_run, config)
            job_id = self._submit_job(job_script)

            if job_id:
                return self._wait_for_completion(job_id, config)
            return False

        except Exception as e:
            self.logger.error(f"SLURM execution failed: {e}")
            return False

    def _create_job_script(self, model_run, config):
        """Create SLURM job script."""
        # Implementation details...
        pass

    def _submit_job(self, job_script):
        """Submit job to SLURM."""
        # Implementation details...
        pass

    def _wait_for_completion(self, job_id, config):
        """Wait for job completion."""
        # Implementation details...
        pass
```

### Entry Points Registration

Register custom backends in your package's `pyproject.toml`:

```toml
[project.entry-points."rompy.run"]
slurm = "mypackage.backends:SlurmRunBackend"

[project.entry-points."rompy.config"]
slurm = "mypackage.config:SlurmConfig"
```

### Backend Discovery

The system automatically discovers registered backends:

```python
from rompy.backends import get_available_backends

# Get all available backends
backends = get_available_backends()
print("Available backends:", list(backends.keys()))

# Use custom backend
from mypackage.config import SlurmConfig

config = SlurmConfig(
    queue="gpu",
    nodes=2,
    partition="compute",
    time_limit="2:00:00"
)

success = model_run.run(backend=config)
```

For complete backend discovery implementation, see `rompy.backends`.

## Postprocessor System

Postprocessors handle model outputs after execution using Pydantic-based configuration classes for type-safe parameter handling.

### Postprocessor Configuration Architecture

```
BasePostprocessorConfig
├── NoopPostprocessorConfig          # Validation-only processor
└── CustomPostprocessorConfig        # User-defined configurations
```

### Configuration Loading

Configurations are loaded from files using entry point discovery:

```python
from rompy.postprocess.config import _load_processor_config

# Load from YAML/JSON file
config = _load_processor_config("processor.yml")

# The loader discovers the config class via entry points
# based on the 'type' field in the file
```

**Configuration File Format:**

```yaml
# processor.yml
type: noop
validate_outputs: true
timeout: 3600
env_vars:
  DEBUG: "1"
  LOG_LEVEL: "INFO"
```

For complete postprocessor configuration documentation, see `rompy.postprocess.config`.

### Built-in Postprocessor Configurations

**NoopPostprocessorConfig:**

The no-operation processor validates outputs without additional processing:

```python
from rompy.postprocess.config import NoopPostprocessorConfig

config = NoopPostprocessorConfig(
    validate_outputs=True,
    timeout=3600,
    env_vars={"DEBUG": "1"}
)

results = model_run.postprocess(processor=config)
```

**Key Parameters:**

* `validate_outputs`: Validate model outputs (default: False)
* `timeout`: Maximum processing time in seconds (60-86400)
* `env_vars`: Environment variables as string key-value pairs
* `working_dir`: Working directory for processing operations

### Usage Patterns

**Programmatic Usage:**

```python
from rompy.postprocess.config import NoopPostprocessorConfig

# Create configuration
config = NoopPostprocessorConfig(
    validate_outputs=True,
    timeout=7200
)

# Use in postprocessing
results = model_run.postprocess(processor=config)

if results["success"]:
    print("Post-processing completed")
else:
    print(f"Post-processing failed: {results.get('error')}")
```

**From Configuration Files:**

```python
from rompy.postprocess.config import _load_processor_config

# Load configuration
config = _load_processor_config("processor.yml")

# Use configuration
results = model_run.postprocess(processor=config)
```

**CLI Usage:**

```bash
# Post-process with configuration file
rompy postprocess model.yml --processor-config processor.yml

# Run complete pipeline with postprocessor
rompy pipeline model.yml \
  --run-backend local \
  --processor-config processor.yml

# Validate postprocessor configuration
rompy backends validate processor.yml --processor-type noop
```

### Custom Postprocessor Configurations

Create custom postprocessor configurations by inheriting from `BasePostprocessorConfig`:

```python
from rompy.postprocess.config import BasePostprocessorConfig
from pydantic import Field
from typing import Optional, List

class AnalysisPostprocessorConfig(BasePostprocessorConfig):
    """Configuration for analysis postprocessor."""
    
    type: str = Field("analysis", const=True)
    
    # Analysis-specific fields
    metrics: List[str] = Field(
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
        description="Configuration for plot generation"
    )
    
    def get_postprocessor_class(self):
        """Return the postprocessor implementation class.
        
        This method is called to instantiate the actual postprocessor
        that will handle the processing logic.
        """
        from mypackage.postprocess import AnalysisPostprocessor
        return AnalysisPostprocessor
```

### Custom Postprocessor Implementation

Implement the postprocessor class that uses your configuration:

```python
from pathlib import Path
from typing import Dict, Any
import logging

class AnalysisPostprocessor:
    """Analysis postprocessor implementation."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def process(
        self,
        model_run,
        config: AnalysisPostprocessorConfig,
        **kwargs
    ) -> Dict[str, Any]:
        """Process model outputs using configuration.
        
        Args:
            model_run: The ModelRun instance
            config: The AnalysisPostprocessorConfig instance
            **kwargs: Additional processor-specific parameters
            
        Returns:
            dict: Processing results with success status
        """
        try:
            output_dir = Path(model_run.output_dir) / model_run.run_id
            
            # Validate outputs if requested
            if config.validate_outputs:
                self._validate_outputs(output_dir)
            
            # Calculate metrics from configuration
            metrics = self._calculate_metrics(
                output_dir,
                metrics=config.metrics,
                output_format=config.output_format
            )
            
            # Generate plots if configured
            plots = []
            if config.plot_config:
                plots = self._generate_plots(output_dir, config.plot_config)
            
            # Compress outputs if requested
            if config.compress:
                compressed_files = self._compress_outputs(output_dir)
            else:
                compressed_files = []
            
            return {
                "success": True,
                "metrics": metrics,
                "plots": plots,
                "compressed_files": compressed_files,
                "message": "Analysis completed successfully"
            }
            
        except Exception as e:
            self.logger.exception(f"Analysis failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Analysis failed: {e}"
            }
    
    def _validate_outputs(self, output_dir):
        """Validate that expected outputs exist."""
        # Implementation details
        pass
    
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

### Entry Points Registration

Register custom postprocessor configurations and implementations in `pyproject.toml`:

```toml
[project.entry-points."rompy.postprocess.config"]
analysis = "mypackage.postprocess.config:AnalysisPostprocessorConfig"

[project.entry-points."rompy.postprocess"]
analysis = "mypackage.postprocess:AnalysisPostprocessor"
```

### Configuration Discovery

The system automatically discovers registered postprocessor configurations:

```python
from importlib.metadata import entry_points

# Get all available postprocessor configurations
eps = entry_points(group="rompy.postprocess.config")
available_configs = {ep.name: ep.load() for ep in eps}

print("Available postprocessor configurations:", list(available_configs.keys()))

# Use custom configuration
from mypackage.postprocess.config import AnalysisPostprocessorConfig

config = AnalysisPostprocessorConfig(
    validate_outputs=True,
    metrics=["mean", "variance", "peak"],
    output_format="netcdf",
    compress=True,
    plot_config={"figsize": (10, 8), "dpi": 300}
)

success = model_run.postprocess(processor=config)
```

### Configuration Validation

Pydantic provides comprehensive validation for postprocessor configurations:

```python
from rompy.postprocess.config import NoopPostprocessorConfig
from pydantic import ValidationError

try:
    # Invalid timeout (too short)
    config = NoopPostprocessorConfig(timeout=30)
except ValidationError as e:
    for error in e.errors():
        print(f"Field {error['loc']}: {error['msg']}")

try:
    # Invalid env_vars type
    config = NoopPostprocessorConfig(env_vars=["invalid"])
except ValidationError as e:
    print(f"Validation error: {e}")
```

**Common Validation Rules:**

* `timeout`: Must be between 60 and 86400 seconds
* `env_vars`: Must be string key-value pairs
* `working_dir`: Must exist if specified
* `validate_outputs`: Must be boolean
* Custom fields: Validated according to field definitions

### Configuration Serialization

Save and load configurations for reproducibility:

```python
import json
from rompy.postprocess.config import NoopPostprocessorConfig

# Create configuration
config = NoopPostprocessorConfig(
    validate_outputs=True,
    timeout=7200,
    env_vars={"DEBUG": "1"}
)

# Serialize to dict
config_dict = config.model_dump()

# Save to file
with open("processor_config.json", "w") as f:
    json.dump(config_dict, f, indent=2)

# Load from file
with open("processor_config.json") as f:
    loaded_data = json.load(f)

# Reconstruct configuration
reconstructed = NoopPostprocessorConfig(**loaded_data)
```

### Schema Generation

Generate JSON schemas for validation and documentation:

```python
from rompy.postprocess.config import NoopPostprocessorConfig
import json

# Generate JSON schema
schema = NoopPostprocessorConfig.model_json_schema()

# Save for external validation
with open("noop_schema.json", "w") as f:
    json.dump(schema, f, indent=2)

# Use schema for validation
import jsonschema

config_data = {
    "validate_outputs": True,
    "timeout": 3600
}

try:
    jsonschema.validate(config_data, schema)
    print("Configuration is valid")
except jsonschema.ValidationError as e:
    print(f"Validation error: {e.message}")
```

### Integration with Pipeline

Postprocessor configurations integrate seamlessly with pipeline backends:

```python
from rompy.pipeline import LocalPipelineBackend
from rompy.backends import DockerConfig
from rompy.postprocess.config import NoopPostprocessorConfig

# Create pipeline backend
pipeline = LocalPipelineBackend()

# Configure run backend
run_config = DockerConfig(
    image="swan:latest",
    cpu=8,
    memory="16g",
    timeout=7200
)

# Configure postprocessor
processor_config = NoopPostprocessorConfig(
    validate_outputs=True,
    timeout=3600
)

# Execute pipeline
results = pipeline.execute(
    model_run=model_run,
    run_backend=run_config,
    processor_config=processor_config,
    cleanup_on_failure=False
)

if results["success"]:
    print(f"Pipeline completed: {results['stages_completed']}")
else:
    print(f"Pipeline failed: {results.get('error')}")
```

## Best Practices

### Configuration Management

1. **Use Version Control**: Store configuration files in version control
2. **Environment Variables**: Use environment variables for sensitive data
3. **Validation**: Always validate configurations before production use
4. **Documentation**: Document custom configurations thoroughly
5. **Testing**: Test configurations with different scenarios

```python
# Good: Use environment variables for sensitive data
config = LocalConfig(
    env_vars={"API_KEY": os.environ.get("API_KEY")}
)

# Avoid: Hardcoding sensitive data
config = LocalConfig(
    env_vars={"API_KEY": "secret-key-123"}
)
```

### Security Considerations

1. **Container Security**: Use non-root users in containers
2. **Volume Mounts**: Use read-only mounts when possible
3. **Resource Limits**: Set appropriate CPU/memory limits
4. **Environment Variables**: Never store secrets in configuration files

```python
# Secure Docker configuration
config = DockerConfig(
    image="swan:latest",
    user="appuser",  # Non-root user
    volumes=["/data:/app/data:ro"],  # Read-only mount
    cpu=4,  # Resource limit
    memory="4g"  # Memory limit
)
```

### Performance Optimization

1. **Resource Allocation**: Match resources to model requirements
2. **Parallel Execution**: Use MPI for large models
3. **Image Optimization**: Use optimized Docker images
4. **Configuration Caching**: Cache validated configurations
5. **Monitoring**: Track resource usage patterns

```python
# Performance-optimized configuration
config = DockerConfig(
    image="swan:hpc-optimized",
    cpu=16,
    memory="32g",
    mpiexec="mpirun -np 16",
    env_vars={
        "OMP_NUM_THREADS": "1",  # Avoid thread oversubscription
        "MODEL_PRECISION": "double"
    }
)
```

### Error Handling

1. **Graceful Degradation**: Handle errors gracefully
2. **Informative Messages**: Provide clear error messages
3. **Logging**: Log important events and errors
4. **Retry Logic**: Implement retry mechanisms for transient failures
5. **Cleanup**: Ensure proper cleanup on failure

```python
def safe_model_execution(model_run, config):
    """Safely execute model with error handling."""
    try:
        # Validate configuration
        if not config.validate():
            raise ValueError("Invalid configuration")

        # Execute model
        success = model_run.run(backend=config)

        if not success:
            logger.error("Model execution failed")
            return False

        return True

    except Exception as e:
        logger.error(f"Execution error: {e}")
        # Cleanup logic here
        return False
```

## Testing

Backend configurations and implementations should be thoroughly tested.

### Configuration Testing

```python
import pytest
from rompy.backends import LocalConfig
from pydantic import ValidationError

def test_local_config_validation():
    """Test LocalConfig validation."""
    # Valid configuration
    config = LocalConfig(timeout=3600, command="python test.py")
    assert config.timeout == 3600

    # Invalid configuration
    with pytest.raises(ValidationError):
        LocalConfig(timeout=30)  # Too short
```

### Backend Testing

```python
def test_backend_execution():
    """Test backend execution."""
    config = LocalConfig(timeout=600, command="echo 'test'")

    # Mock model run
    mock_model = create_mock_model()

    # Test execution
    backend = config.get_backend_class()()
    success = backend.run(mock_model, config)

    assert success is True
```

### Integration Testing

```python
def test_full_workflow():
    """Test complete workflow with backend."""
    model_run = ModelRun.from_file("test_model.yml")
    config = LocalConfig(timeout=1800)

    # Test full workflow
    success = model_run.run(backend=config)
    results = model_run.postprocess(processor="archive")

    assert success is True
    assert results["success"] is True
```

For comprehensive testing examples, see the test suite in `tests/backends/`.

## Troubleshooting

### Common Issues

**Configuration Validation Errors**
: Use `rompy backends validate` to check configuration syntax and validate against schema.

**Docker Issues**
: Verify Docker installation, image availability, and volume mount permissions.

**Timeout Issues**
: Adjust timeout values based on model complexity and system performance.

**Memory Issues**
: Monitor memory usage and adjust allocation in Docker configurations.

**Permission Issues**
: Check file permissions for volume mounts and working directories.

### Debug Mode

Enable debug logging for detailed troubleshooting:

```python
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

# Create debug configuration
config = LocalConfig(
    timeout=3600,
    env_vars={"LOG_LEVEL": "DEBUG", "MODEL_DEBUG": "true"}
)
```

### Getting Help

1. **Check Documentation**: Review [backends](../backends.md) and [api](../api.md)
2. **Validate Configuration**: Use `rompy backends validate`
3. **Check Logs**: Review execution logs for error details
4. **Test Incrementally**: Start with simple configurations
5. **Community Support**: Check GitHub issues and discussions

For additional help, see the troubleshooting section in [backends](../backends.md) or file an issue on GitHub.

## API Reference

For complete API documentation, see:

* [api](../api.md) - Complete API documentation
* `rompy.backends.config.BaseBackendConfig` - Base configuration class
* `rompy.backends.config.LocalConfig` - Local execution configuration
* `rompy.backends.config.DockerConfig` - Docker execution configuration
* `rompy.run` - Backend implementation classes
* `rompy.backends.postprocessors` - Postprocessor implementations
* `rompy.backends` - Backend discovery and registry

This reference covers the key concepts and patterns for working with Rompy's backend system. For implementation details and complete parameter documentation, refer to the API documentation.