# SWAN Model Guide

## Installation

To use the SWAN model with Rompy, install the dedicated plugin:

```bash
pip install rompy-swan
```

## Overview

SWAN (Simulating WAves Nearshore) is a third-generation wind-wave model that computes random, short-crested waves in coastal regions and inland waters. With Rompy, you can configure SWAN simulations using Python objects that are validated with Pydantic, ensuring consistent and reproducible model setups.

## Detailed Documentation

For comprehensive documentation on using SWAN with Rompy, visit: https://rom-py.github.io/rompy-swan

## Worked Examples

For practical, hands-on examples of how to use SWAN with Rompy, please see the following notebooks:

- **[SWAN Procedural Example](notebooks/swan/example_procedural.ipynb)**: A basic demonstration of a procedural SWAN run.
- **[SWAN Sensitivity Example](notebooks/swan/example_sensitivity.ipynb)**: An example of how to run a sensitivity analysis with SWAN.
- **[SWAN Boundary Conditions](notebooks/swan/boundary/boundnest1.ipynb)**: Examples of how to set up different types of boundary conditions.

## Next Steps

- Review the [Backends Guide](backends.md) for detailed execution options
- Learn about [Configuration Deep Dive](configuration_deep_dive.md) for detailed configuration options
- Check the [Progressive Tutorials](progressive_tutorials.md) for practical examples