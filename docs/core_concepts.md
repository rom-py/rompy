# Core Concepts

> [!NOTE]
> For information about Rompy's formatting and logging system, see [formatting_and_logging](formatting_and_logging.md).
> 
> For details on using the command line interface, see [cli](cli.md).

This section delves into the fundamental components that make up Rompy's architecture. If you're new to Rompy, start with the [User Guide](user_guide.md) before diving into these concepts.

Rompy is a modular library with configuration and execution separated by design. The core framework consists of two primary concepts:

::: rompy.model.ModelRun
::: rompy.core.config.BaseConfig

At a high level, ModelRun orchestrates the entire model execution process including generation, execution, and post-processing, while configuration objects are responsible for defining the model setup.

## Core Component Categories

### Grid Components

Grids define the spatial domain of models. Rompy provides several grid types:

::: rompy.core.grid.BaseGrid
::: rompy.core.grid.RegularGrid

### Data Components

Data objects represent and handle input data for models:

::: rompy.core.data.DataBlob
::: rompy.core.data.DataGrid
::: rompy.core.source.SourceBase
::: rompy.core.source.SourceFile
::: rompy.core.source.SourceIntake

### Boundary Components

Boundary conditions specify model forcing at domain edges:

::: rompy.core.boundary.BoundaryWaveStation
::: rompy.core.source.SourceWavespectra

### Spectrum Components

Spectral representations for wave models:

::: rompy.core.spectrum.LogFrequency

## Architecture Patterns

### Configuration Validation

All Rompy configurations use Pydantic models, providing type safety and validation:

- Automatic validation of configuration parameters
- Clear error messages for invalid configurations
- Serialization/deserialization capabilities for reproducibility

### Plugin Architecture

Rompy's plugin system allows for extensibility:

- Model configurations via `rompy.config` entry points
- Execution backends via `rompy.run` entry points
- Post-processors via `rompy.postprocess` entry points

### Backend Abstraction

Execution backends abstract the computational environment:

- Local execution for development
- Docker execution for containerized workflows
- HPC execution for high-performance computing
- Cloud execution for scalable computing

## Best Practices

### Configuration Design

1. **Use Type Safety**: Leverage Pydantic models for configuration validation
2. **Modular Configuration**: Keep components modular and reusable
3. **Serialization**: Ensure configurations are fully serializable for reproducibility
4. **Documentation**: Document configuration options and default values

### Model Integration

1. **Template-based Generation**: Use cookiecutter templates for model input generation
2. **Environment Agnostic**: Design models to run in different computational environments
3. **Data Abstraction**: Abstract data sources to support multiple input formats

## Next Steps

- For detailed configuration options, see [Configuration Deep Dive](configuration_deep_dive.md)
- To understand the overall architecture, see [Architecture Overview](architecture_overview.md)
- For practical examples of using these concepts, see [Progressive Tutorials](progressive_tutorials.md)
- To learn about implementing different models, see [Models](models.md)