# Models

## Overview

Rompy provides model-specific implementations for various ocean, wave, and hydrodynamic models. Each model implementation includes configuration classes, grid definitions, data handling, and execution backends. For basic concepts about models, see the [Getting Started Guide](getting_started.md).

## Supported Models

Rompy currently supports the following models, each with a varying level of maturity:

- **SWAN**: Spectral Wave Nearshore model (install with `pip install rompy-swan`)
- **SCHISM**: Semi-implicit Cross-scale Hydroscience Integrated Modeling System (install with `pip install rompy-schism`)
- **XBeach**: A numerical model for the simulation of nearshore and coastal processes (install with `pip install rompy-xbeach`)
- **WAVEWATCH III**: A third-generation wave model developed at NOAA/NCEP (install with `pip install rompy-ww3`)

## Model Maturity

The integration of each model into the Rompy framework is at a different stage of development. Here is a summary of the current status:

- **SWAN**: Full implementation. The SWAN integration is the most mature and has the most features.
- **SCHISM**: Full implementation. Less well tested and still under active development.
- **XBeach**: Under active development
- **WAVEWATCH III**: Under active development.

For more detailed information on each model, please refer to their specific guides:

- [SWAN Guide](swan_guide.md)
- [SCHISM Guide](schism_guide.md)
- [XBeach Guide](xbeach_guide.md)
- [WAVEWATCH III Guide](ww3_guide.md)

## Model-Specific Documentation

- **SWAN**: [https://rom-py.github.io/rompy-swan](https://rom-py.github.io/rompy-swan)
- **SCHISM**: [https://rom-py.github.io/rompy-schism](https://rom-py.github.io/rompy-schism)
- **XBeach**: [https://rom-py.github.io/rompy-xbeach](https://rom-py.github.io/rompy-xbeach)
- **WAVEWATCH III**: [https://rom-py.github.io/rompy-ww3](https://rom-py.github.io/rompy-ww3)

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

## Model Integration

Models integrate with Rompy's core framework through:

- Pydantic-based configuration classes for type safety
- XArray accessors for data manipulation
- Intake drivers for data catalog integration
- Cookiecutter templates for model setup
- Unified execution backends for consistent deployment

## Best Practices

When working with models:

1. **Use Type Safety**: Leverage Pydantic models for configuration validation
2. **Modular Design**: Keep model components modular and reusable
3. **Documentation**: Document model-specific parameters and usage
4. **Testing**: Include comprehensive tests for model implementations
5. **Examples**: Provide clear examples for common use cases

## Extending Model Support

To add support for a new model, see the [Extending Models](extending_models.md) guide which provides detailed information about creating new model implementations.

## Next Steps

For further information on working with models in Rompy:

- Check the [Extending Models](extending_models.md) guide to add new model support
- Follow the [Progressive Tutorials](progressive_tutorials.md) for hands-on examples
- Review [Configuration Deep Dive](configuration_deep_dive.md) for advanced configuration techniques
- Understand the [Architecture Overview](architecture_overview.md) for component integration
- Explore [Common Workflows](common_workflows.md) for practical implementation patterns

