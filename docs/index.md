# Welcome to Rompy's Documentation

## *Streamlining Ocean Modeling with Python*

Rompy (Relocatable Ocean Modelling in PYthon) is a comprehensive, modular Python library designed to simplify the setup, configuration, execution, and analysis of coastal ocean models. It combines templated model configuration with powerful xarray-based data handling and pydantic validation, enabling users to efficiently generate model control files and input datasets for a variety of ocean and wave models.

---

## Why Rompy?

Rompy was developed to address common pain points in the ocean modeling workflow:

- **Complex Model Setup & Configuration**: Traditional model setup can be a convoluted process involving manual editing of text files and scripts, making it error-prone and difficult to reproduce.
- **Data Handling Complexity**: Ocean models require a wide variety of data formats for forcing, boundary conditions, and validation, each with its own complexities.
- **Environment-Specific Execution**: Running models across different environments (local, Docker, HPC) often requires significant changes to the execution scripts and environment setup.
- **Reproducibility & Version Control**: It can be challenging to version control a complete model configuration, including the exact data and software versions used.
- **Model-Specific Complexity**: Each model has its own unique set of tools and conventions, making it difficult to switch between models or to couple them.

---

## History

- **2021**: Initial development by Paul Branson.
- **Sept 2022**: Synergies with internal efforts at Oceanum lead to initialisation of collaboration.
- **Currently**: Supported through the ROAM Gen 3 effort.

All code is open source and available under an Apache license. You can find a list of contributors [here](https://github.com/rom-py/rompy/blob/main/CONTRIBUTORS) and the project's history [here](https://github.com/rom-py/rompy/blob/main/HISTORY.rst).



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

New to Rompy? Our **[Getting Started Guide](getting_started.md)** will walk you through installation, core concepts, and running your first model simulation.

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
