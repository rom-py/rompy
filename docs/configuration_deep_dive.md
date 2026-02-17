# Configuration Deep Dive

This section provides detailed information on configuring different aspects of ocean models in Rompy, covering advanced configuration options, best practices, and common patterns. If you're new to Rompy, start with the [Getting Started Guide](getting_started.md) before reading this section.

## Advanced Configuration Patterns

### Configuration Validation

Leverage Pydantic's validation capabilities:

```python
from pydantic import BaseModel, validator
from datetime import datetime

class ValidatedModelRun(BaseModel):
    start_time: datetime
    end_time: datetime
    duration_limit: int = 86400  # Maximum duration in seconds

    @validator('end_time')
    def end_after_start(cls, v, values):
        if 'start_time' in values and v < values['start_time']:
            raise ValueError('end_time must be after start_time')
        return v

    @validator('end_time')
    def duration_limit_check(cls, v, values):
        if 'start_time' in values:
            duration = (v - values['start_time']).total_seconds()
            if duration > values['duration_limit']:
                raise ValueError(f'duration exceeds limit of {values["duration_limit"]} seconds')
        return v
```

### Configuration Serialization

Save and load configurations for reproducibility:

```python
import json
from pathlib import Path

# Save configuration
config_dict = model_run.config.model_dump()
with open("model_config.json", "w") as f:
    json.dump(config_dict, f, indent=2, default=str)

# Load configuration
with open("model_config.json", "r") as f:
    config_data = json.load(f)

# reconstructed_config = ModelConfig(**config_data)
```

## Best Configuration Practices

### 1. Use Environment Variables for Sensitive Information

```python
import os
from pydantic import BaseSettings

class ModelSettings(BaseSettings):
    api_key: str = os.getenv("MODEL_API_KEY", "")
    data_dir: str = os.getenv("MODEL_DATA_DIR", "./data")

    class Config:
        env_file = ".env"
```

### 2. Separate Runtime from Configuration

Keep runtime information separate from model configuration:

- Configuration: What the model is (grid, physics, etc.)
- Runtime: When and where the model runs (time periods, output locations, etc.)

### 3. Use Configuration Factories

Create factory functions for complex configurations:

```python
def create_operational_config(model_type: str, grid_resolution: float):
    """Factory function to create operational model configurations."""
    if model_type == "swan":
        # Return SWAN-specific config
        pass
    elif model_type == "schism":
        # Return SCHISM-specific config
        pass
    else:
        raise ValueError(f"Unsupported model type: {model_type}")
```

### 4. Validate Configuration Early

Use Pydantic's validation to catch errors early:

```python
from pydantic import BaseModel, validator, ValidationError

try:
    # This will raise ValidationError if validation fails
    model_run = ModelRun(**config_dict)
except ValidationError as e:
    print(f"Configuration validation error: {e}")
```

## Common Configuration Patterns

### Pattern 1: Template-Based Configuration

```python
from pydantic import BaseModel
from typing import Dict, Any

class TemplateConfig(BaseModel):
    template_dir: str
    template_files: Dict[str, str]  # {logical_name: template_filename}
    parameter_mapping: Dict[str, str]  # {config_param: template_var}

    def render_template(self, output_dir: str, **kwargs):
        """Render templates with provided configurations."""
        # Implementation to render templates using cookiecutter or similar
        pass
```

### Pattern 2: Multi-Source Data Configuration

```python
from typing import List
from pydantic import BaseModel

class MultiSourceConfig(BaseModel):
    primary_source: DataSource
    secondary_sources: List[DataSource] = []
    fallback_source: Optional[DataSource] = None
    merge_strategy: str = "priority"  # priority, interpolate, etc.
```

## Troubleshooting Common Configuration Issues

### Issue: Configuration Validation Fails

**Symptoms**: Pydantic validation errors when creating model objects

**Solution**:

1. Check the error message for specific validation issues
2. Verify data types match expected types
3. Use the model's schema to understand field requirements:

   ```python
   print(ModelRun.model_json_schema())
   ```

### Issue: Configuration Fails on Different Systems

**Symptoms**: Configuration works locally but fails in Docker or HPC

**Solution**:

1. Use relative paths where possible
2. Make paths configurable through environment variables
3. Ensure file permissions are appropriate

## Model-Specific Configuration

Different ocean models have specific configuration requirements. See the [Model-Specific Guides](models.md) for detailed information about configuring SWAN, SCHISM, and other supported models.

## Next Steps

- Review the [Model-Specific Guides](models.md) for configuration details for specific models
- Learn about [Plugin Architecture](plugin_architecture.md) to extend configuration capabilities
- Explore [Backends](backends.md) for different execution environments

