# Architecture Overview

This document provides a comprehensive overview of Rompy's architecture, explaining the advanced design patterns and component interactions. For basic concepts, please see the [User Guide](user_guide.md).

Rompy follows a modular, plugin-based architecture that separates concerns between configuration, execution, and post-processing:

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   ModelRun      │    │   Configuration  │    │   Execution     │
│                 │───▶│                  │───▶│                 │
│ - Time periods  │    │ - Grid           │    │ - Local backend │
│ - Output dir    │    │ - Data sources   │    │ - Docker backend│
│ - Run ID        │    │ - Physics params │    │ - HPC backend   │
│ - etc.          │    │ - Templates      │    │ - etc.          │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │
         │    ┌──────────────────┐
         └───▶│ Post-processing  │
              │                  │
              │ - Custom         │
              │   processors     │
              │ - Result analysis│
              │ - Visualization  │
              └──────────────────┘
```

## Advanced Architecture Patterns

### 1. Separation of Concerns
- Configuration (what to compute) is separate from execution (how to compute)
- Model setup is independent of execution environment
- Data sources are abstracted from model implementation

### 2. Composition over Inheritance
- Complex configurations built by composing simpler components
- Backends compose different capabilities rather than inheriting behavior

### 3. Type Safety with Pydantic
- Configuration objects validated at runtime
- Clear interfaces with type hints
- Automatic serialization/deserialization

### 4. Late Binding
- Execution backends resolved at runtime
- Enables the same configuration to run in different environments

## Plugin Architecture

Rompy uses Python entry points for extensibility:

### Entry Points

1. **`rompy.config`**: Model configuration classes
2. **`rompy.run`**: Execution backends
3. **`rompy.postprocess`**: Post-processing modules
4. **`rompy.source`**: Data source implementations

### Extending Functionality

New components can be added through the plugin system:

```python
# Example: Adding a new model configuration
# Register in setup.py/pyproject.toml:
# [project.entry-points."rompy.config"]
# mymodel = "mypackage.config:MyModelConfig"

class MyModelConfig(BaseConfig):
    model_type: Literal["mymodel"] = "mymodel"
    # Custom model configuration attributes
```

## Data Flow Architecture

### 1. Configuration Phase
```
User Code → Pydantic Models → Validation → Configuration Object
```

### 2. Generation Phase
```
ModelRun + Config → Template Rendering → Model Input Files
```

### 3. Execution Phase
```
ModelRun + Backend Config → Backend Execution → Model Output
```

### 4. Post-processing Phase
```
ModelRun + Output → Processor → Processed Results
```

## Design Principles

### 1. Reproducibility
- Model configurations are fully serializable
- Same configuration produces identical results across environments
- Execution context tracked and logged

### 2. Extensibility
- Plugin system allows adding new models without changing core code
- Backend-agnostic design supports multiple execution environments
- Hook points available for custom processing

### 3. Environment Agnostic
- The same model configuration can run in multiple environments (local, HPC, cloud)
- Execution backends are resolved at runtime based on configuration

## Module Structure

### Core Modules
- `rompy.model`: Contains the main `ModelRun` class
- `rompy.core`: Basic abstractions (config, grid, data, source)
- `rompy.backends`: Backend implementations and configuration
- `rompy.run`: Run backend implementations
- `rompy.postprocess`: Post-processing implementations
- `rompy.pipeline`: Pipeline orchestration
- `rompy.logging`: Logging and formatting framework

### Key Classes and Their Responsibilities

| Class | Module | Responsibility |
|-------|--------|----------------|
| ModelRun | rompy.model | Main orchestrator for model runs |
| BaseConfig | rompy.core.config | Base configuration model |
| BaseGrid | rompy.core.grid | Base grid definition |
| DataGrid | rompy.core.data | Data grid abstraction |
| SourceBase | rompy.core.source | Base data source interface |
| LocalConfig | rompy.backends | Local backend configuration |
| DockerConfig | rompy.backends | Docker backend configuration |
| LocalRunBackend | rompy.run | Local execution backend |
| DockerRunBackend | rompy.run.docker | Docker execution backend |

## Integration Points

Rompy integrates with various external systems:

### Data Systems
- NetCDF files via xarray
- Intake catalogs for data discovery
- Various file formats through fsspec

### Execution Systems
- Docker for containerized execution
- HPC systems via job schedulers
- Cloud platforms for distributed computing

### Development Tools
- Pydantic for configuration validation
- Cookiecutter for template-based generation
- Standard Python logging

## Future Architecture Considerations

### Scalability
- Support for distributed model components
- Parallel execution of ensemble members
- Asynchronous job submission

### Extensibility
- Additional plugin interfaces for custom workflows
- Machine learning integration for parameter estimation
- Enhanced visualization capabilities

## Next Steps

- Review the [Plugin Architecture](plugin_architecture.md) for more details on extending Rompy
- Check the [Developer Guide](developer/index.md) for advanced development topics
- Look at the [API Reference](api.md) for detailed class documentation