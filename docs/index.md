# Welcome to Rompy's Documentation

## *Streamlining Ocean Modeling with Python*

Rompy (Relocatable Ocean Modelling in PYthon) is a comprehensive, modular Python library designed to simplify the setup, configuration, execution, and analysis of coastal ocean models. It combines templated model configuration with powerful xarray-based data handling and pydantic validation, enabling users to efficiently generate model control files and input datasets for a variety of ocean and wave models.

---

## Key Features

- **Modular Architecture**: Clean separation of configuration and execution logic supporting multiple ocean models
- **Template-Based Configuration**: Reproducible model configuration using cookiecutter templates with pydantic validation
- **Unified Data Interface**: Consistent interfaces for grids, data sources, boundary conditions, and spectra
- **Extensible Plugin System**: Support for new models, data sources, backends, and postprocessors
- **Multiple Execution Backends**: Support for local, Docker, and HPC execution environments
- **Rich Logging & Formatting**: Comprehensive, visually appealing logging with formatted output and diagnostics
- **Pydantic Validation**: Strong typing and validation throughout the API for robust error handling

---

## Getting Started

New to Rompy? Start with our comprehensive guides:

- [**Installation Guide**](installation.md) - Prerequisites, installation methods, and environment setup
- [**User Guide**](user_guide.md) - Complete tutorial from installation to running your first model
- [**Quickstart**](quickstart.md) - Basic example to quickly get up and running
- [**Progressive Tutorials**](progressive_tutorials.md) - Step-by-step tutorials building from basic to advanced usage

---

## Tutorials & Examples

Learn through practical examples:

- [**Progressive Tutorials**](progressive_tutorials.md) - Structured learning path from basic to advanced usage
- [**Practical Examples**](examples.md) - Real-world scenarios with complete code examples
- [**Common Workflows**](common_workflows.md) - Typical ocean modeling patterns and best practices

---

## Model Support

Rompy currently supports multiple ocean and wave models with plans for continued expansion:

- [**Models Overview**](models.md) - Introduction to supported models
- [**SWAN Guide**](swan_guide.md) - Comprehensive guide for SWAN model configuration
- [**SCHISM Guide**](schism_guide.md) - Detailed configuration for SCHISM model
- [**Extending Models**](extending_models.md) - Guide to adding new model implementations

---

## Advanced Topics

For more complex implementations and custom extensions:

- [**Backends**](backends.md) - Execution backends for different environments
- [**CLI**](cli.md) - Command-line interface for automation
- [**Plugin Architecture**](plugin_architecture.md) - Extending Rompy with custom plugins
- [**Architecture Overview**](architecture_overview.md) - System architecture and component relationships

---

## Development & Contribution

For those looking to contribute or extend Rompy:

- [**Contribution Guidelines**](contributing.md) - How to contribute to the project
- [**Development Setup**](developer/index.md) - Getting started with development
- [**Testing Guide**](testing_guide.md) - Writing and running tests for Rompy
- [**Backend Reference**](developer/backend_reference.md) - Technical details for backend development

---

## Resources

- [**FAQ**](faq.md) - Common questions and troubleshooting solutions
- [**Demo**](demo.md) - Interactive demonstration of Rompy capabilities
- [**API Reference**](api.md) - Complete API documentation with usage examples

---

## Quick Example

Here's a simple example to demonstrate Rompy's capabilities:

```python
from rompy.model import ModelRun
from rompy.core.config import BaseConfig
from rompy.core.time import TimeRange
from datetime import datetime

# Create a basic model configuration
config = BaseConfig()

# Create a model run instance with time range
run = ModelRun(
    run_id="my_first_run",
    period=TimeRange(
        start=datetime(2023, 1, 1),
        end=datetime(2023, 1, 2),
        interval="1H",  # Hourly intervals
    ),
    config=config,
    output_dir="./output",
)

# Generate model input files
run.generate()

# Execute the model run
from rompy.backends import LocalConfig
backend_config = LocalConfig(timeout=3600, command="echo 'Running model...'")
success = run.run(backend=backend_config)

if success:
    print("Model run completed successfully!")
else:
    print("Model run failed.")
```

---

## Support & Community

- [**GitHub Repository**](https://github.com/rom-py/rompy) - Source code and issue tracking
- [**Contributing**](contributing.md) - How to contribute to the project
- [**FAQ**](faq.md) - Answers to common questions

**Note**: Rompy is under active development—features, model support, and documentation are continually evolving. Contributions and feedback are welcome!
