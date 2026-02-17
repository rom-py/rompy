# Demonstration Notebooks

## Thumbnails Gallery

The following demonstration notebooks showcase various aspects of Rompy's functionality:

* [Rompy Core Features](notebooks/common/rompy_core_features.ipynb) - Basic demonstration of Rompy features
* [SWAN Basic Demo](notebooks/swan/example_procedural.ipynb) - Procedural configuration of SWAN models
* [SWAN Sensitivity Demo](notebooks/swan/example_sensitivity.ipynb) - Sensitivity analysis with SWAN models
* [SWAN Boundnest1](notebooks/swan/boundary/boundnest1.ipynb) - Boundary conditions example using boundnest1
* [SWAN Boundspec Segment](notebooks/swan/boundary/boundspec_segment.ipynb) - Boundary conditions example using boundspec_segment
* [SWAN Boundspec Side](notebooks/swan/boundary/boundspec_side.ipynb) - Boundary conditions example using boundspec_side
* [SCHISM Demo](notebooks/schism/schism_demo.ipynb) - SCHISM model configuration example
* [XBEACH Basic](notebooks/xbeach/example_procedural.ipynb) - Basic XBEACH configuration
* [XBEACH Forcing](notebooks/xbeach/forcing-demo.ipynb) - XBEACH forcing example

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