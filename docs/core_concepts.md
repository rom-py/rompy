# Core Concepts

This section explores the fundamental components that make up Rompy's architecture. If you're new to Rompy, start with the [Getting Started Guide](getting_started.md) before diving into these concepts.

Rompy is a modular library with configuration and execution separated by design. The core framework consists of two primary concepts:

::: rompy.model.ModelRun
::: rompy.core.config.BaseConfig

At a high level, ModelRun orchestrates the entire model execution process including generation, execution, and post-processing, while configuration objects are responsible for defining the model setup.

## Data Management System

Rompy's data management system is designed to provide a unified and flexible interface for handling the diverse data requirements of ocean models. It is built on three key abstractions: Source, Grid, and Data.

### Source Abstraction

The source abstraction is a plugin-based system that allows Rompy to access data from a wide variety of sources through a unified interface. This enables users to seamlessly switch between different data sources without changing their model configuration.

- **Purpose**: Plugin-based system for accessing diverse data sources through a unified interface.
- **Key implementations**:
    - `SourceFile`: For accessing local or remote files via xarray.
    - `SourceIntake`: For accessing datasets from an Intake catalog.
    - `SourceDatamesh`: For integration with the Oceanum Datamesh API.
    - `SourceWavespectra`: For reading data using the `wavespectra` library.
- **Architecture**: Uses Python entry points for dynamic plugin loading, enabling type-safe source selection via Pydantic discriminated unions.
- **Benefits**: Provides access to a large catalog of datasets from different sources through a common API.

### Grid Abstraction

The grid abstraction is used to define the spatial domains for model execution, with built-in support for coordinate system management.

- **Purpose**: Defines spatial domains for model execution with coordinate system management.
- **Key implementations**:
    - `BaseGrid`: The foundation class for all grid types.
    - `RegularGrid`: For structured rectangular grids.
    - `UnstructuredGrid`: For unstructured grids.
- **Features**: Boundary point extraction, bounding box calculations, CRS transformations, and plotting capabilities.
- **Inheritance**: These base grid types are inherited by model-specific grid implementations (e.g., `SwanGrid`, `SchismGrid`, `XBeachGrid`) to add model-specific functionality.

### Data Abstraction

The data abstraction provides a unified interface for ingesting, filtering, and preparing data for model consumption.

- **Purpose**: Unified interface for ingesting, filtering, and preparing data for model consumption.
- **Three-tier hierarchy**:
    - `DataBlob`: For basic file operations (copy/link).
    - `DataPoint`: For timeseries data with temporal filtering.
    - `DataGrid`: For spatial data with grid and time filtering, as well as cropping and visualization capabilities.
- **Processing pipeline**: Source opening → variable selection → spatial/temporal filtering → coordinate transformation → model-specific formatting.
- **Inheritance**: These base data types are inherited by model-specific data implementations (e.g., `SwanDataGrid`, `SchismDataGrid`, `XBeachDataGrid`) to add model-specific functionality.


## Core Component Categories


### Grid Components

Grids define the spatial domain of models. The base objects described here have base methods and attributes that are used by the core rompy framework when performing things like fetching data. These base objects are inherited by model implementations, with additional required model specific functionality then implemented implemented in top.

Rompy provides several grid types:

::: rompy.core.grid.BaseGrid
::: rompy.core.grid.RegularGrid

### Source Components

Source objects represent different ways to access data for models. They represent the abstraction layer between data inputs and model configurations, allowing for flexibility in data sourcing.

::: rompy.core.source.SourceBase
::: rompy.core.source.SourceFile
::: rompy.core.source.SourceIntake

### Data Components

Data objects represent and handle input data for models:

::: rompy.core.data.DataBlob
::: rompy.core.data.DataGrid

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

## Notebook Examples

For a practical, hands-on example of the core concepts, please see the following notebook:

- **[Core Features](notebooks/common/rompy_core_features.ipynb)**: A demonstration of the core features of Rompy.

## Next Steps

- For detailed configuration options, see [Configuration Deep Dive](configuration_deep_dive.md)
- To understand the overall architecture, see [Architecture Overview](architecture_overview.md)
- For practical examples of using these concepts, see [Progressive Tutorials](progressive_tutorials.md)
- To learn about implementing different models, see [Models](models.md)
