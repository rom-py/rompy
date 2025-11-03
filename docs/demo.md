# Demonstration Notebooks

## Thumbnails Gallery

The following demonstration notebooks showcase various aspects of Rompy's functionality:

* [Demo Notebook](../notebooks/demo.ipynb) - Basic demonstration of Rompy features
* [Templates Demo](../notebooks/templates_demo.ipynb) - Using cookiecutter templates for model setup
* [SWAN Declarative Example](../notebooks/swan/example_declarative.ipynb) - Declarative configuration of SWAN models
* [SWAN Procedural Example](../notebooks/swan/example_procedural.ipynb) - Procedural configuration of SWAN models
* [SWAN Sensitivity Example](../notebooks/swan/example_sensitivity.ipynb) - Sensitivity analysis with SWAN models
* [Oceanum Example](../notebooks/oceanum_example.ipynb) - Using Oceanum data sources
* [SWAN Config Components](../notebooks/swan-config-components.ipynb) - Detailed configuration components for SWAN
* [Physics](../notebooks/physics.ipynb) - Physics-based model configurations
* [SCHISM Procedural](../notebooks/schism_procedural.ipynb) - Procedural configuration of SCHISM models

These notebooks provide practical examples of how to use Rompy for various ocean modeling tasks. Each notebook demonstrates different aspects of the framework, from basic usage to advanced features.

## Getting Started

To run these notebooks:

1. Install Rompy with notebook dependencies:
   ```bash
   pip install rompy[notebooks]
   ```

2. Start Jupyter:
   ```bash
   jupyter notebook
   ```

3. Open any of the demonstration notebooks and run the cells.

## Prerequisites

Some notebooks require additional dependencies:

* **SWAN Notebooks**: SWAN model installation
* **SCHISM Notebooks**: SCHISM model installation
* **Oceanum Notebooks**: Oceanum account and API key

## Contributing Examples

To contribute new demonstration notebooks:

1. Create a new notebook in the appropriate directory
2. Follow the existing structure and conventions
3. Include clear explanations and comments
4. Add the notebook to the gallery in this document
5. Submit a pull request

For more information on contributing, see [contributing](contributing.md).