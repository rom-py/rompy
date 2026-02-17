# API Reference

This section provides comprehensive documentation for the Rompy API, organized by functional modules. Rompy is structured around a modular architecture that supports various ocean and wave models with consistent interfaces for configuration, data handling, execution, and post-processing.

## Core Modules

### Model Execution

The main entry point for running models in Rompy:

::: rompy.model.ModelRun
    options:
      members:
        - __init__
        - generate
        - run
        - postprocess
        - execute

### Core Configuration

Base configuration classes that provide validation and type safety:

::: rompy.core.config.BaseConfig
    options:
      members:
        - __init__
        - model_validate
        - model_dump

### Time Management

Time range and interval handling:

::: rompy.core.time.TimeRange
    options:
      members:
        - __init__
        - to_sequence
        - duration
        - interval

### Grid Systems

Grid definition and management:

::: rompy.core.grid.BaseGrid
    options:
      members:
        - __init__
        - to_dataset
        - bounds

::: rompy.core.grid.RegularGrid
    options:
      members:
        - __init__
        - to_dataset
        - bounds

### Data Handling

Data source and handling components:

::: rompy.core.data.DataBase
    options:
      members:
        - __init__
        - get

::: rompy.core.source.SourceBase
    options:
      members:
        - __init__
        - get_data

### Boundary Conditions

Boundary condition management:

::: rompy.core.boundary.DataBoundary
    options:
      members:
        - __init__
        - get

::: rompy.core.boundary.BoundaryWaveStation
    options:
      members:
        - __init__
        - get

## Backend Systems

### Backend Configuration

Base and specific backend configurations:

::: rompy.backends.config.BaseBackendConfig
    options:
      members:
        - __init__
        - validate
        - get_backend_class

::: rompy.backends.config.LocalConfig
    options:
      members:
        - __init__
        - run

::: rompy.backends.config.DockerConfig
    options:
      members:
        - __init__
        - run

### Backend Execution

Backend execution implementations:

::: rompy.run.docker.DockerRunBackend
    options:
      members:
        - __init__
        - run

::: rompy.run.LocalRunBackend
    options:
      members:
        - __init__
        - run

## CLI Interface

Command-line interface components:

::: rompy.cli
    options:
      members:
        - main
        - run
        - generate

## Formatting and Utilities

Formatting and utility functions:

::: rompy.formatting
    options:
      members:
        - format_box
        - format_table
        - format_header

::: rompy.utils
    options:
      members:
        - load_config
        - save_config
        - validate_config

## Post-processing

Post-processing utilities:

::: rompy.postprocess
    options:
      members:
        - postprocess
        - archive
        - analyze

## Pipeline Management

Pipeline execution components:

::: rompy.pipeline.LocalPipelineBackend
    options:
      members:
        - __init__
        - run

## Spectrum Handling

Spectral data handling:

::: rompy.core.spectrum.Frequency
    options:
      members:
        - __init__
        - to_dataset

::: rompy.core.spectrum.LogFrequency
    options:
      members:
        - __init__
        - to_dataset

## Type Definitions

Common type definitions:

::: rompy.core.types
    options:
      members:
        - TimeRange
        - CoordinateBounds
        - GridType