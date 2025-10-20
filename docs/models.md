# Models

## Overview

ROMPY provides model-specific implementations for various ocean, wave, and hydrodynamic models. Each model implementation includes configuration classes, grid definitions, data handling, and execution backends.

## Supported Models

ROMPY currently supports the following models:

* [SWAN](swan/index.md) - Spectral Wave Nearshore model
* [SCHISM](schism/index.md) - Semi-implicit Cross-scale Hydroscience Integrated Modeling System

## Model Architecture

Each model implementation follows a consistent architecture:

### Configuration

Model-specific configuration classes that define model parameters, grid settings, and data sources.

### Grid

Grid definitions that specify the model domain, resolution, and coordinate system.

### Data

Data handling classes for preparing model input data from various sources.

### Execution

Backend configurations for running the model in different environments (local, Docker, HPC).

### Postprocessing

Classes for analyzing and visualizing model output.

## Extending ROMPY

To add support for a new model:

1. Create a new model package in the `rompy` namespace
2. Implement the required base classes:
   * `BaseModel` - Model configuration and execution
   * `BaseGrid` - Grid definition and handling
   * `DataSource` - Data input handling
3. Add backend support for execution environments
4. Implement postprocessing capabilities
5. Add documentation and examples

## Model Integration

Models integrate with ROMPY's core framework through:

* Pydantic-based configuration classes for type safety
* XArray accessors for data manipulation
* Intake drivers for data catalog integration
* Cookiecutter templates for model setup
* Unified execution backends for consistent deployment

## Best Practices

When working with models:

1. **Use Type Safety**: Leverage Pydantic models for configuration validation
2. **Modular Design**: Keep model components modular and reusable
3. **Documentation**: Document model-specific parameters and usage
4. **Testing**: Include comprehensive tests for model implementations
5. **Examples**: Provide clear examples for common use cases

## Model-Specific Documentation

For detailed information about each supported model, see:

* [SWAN Model](swan/index.md) - Spectral Wave Nearshore model documentation
* [SCHISM Model](schism/index.md) - Semi-implicit Cross-scale Hydroscience Integrated Modeling System documentation