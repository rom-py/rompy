# SCHISM Model Guide

## Installation

To use the SCHISM model with Rompy, install the dedicated plugin:

```bash
pip install rompy-schism
```

## Overview

SCHISM (Semi-implicit Cross-scale Hydroscience Integrated System Model) is an unstructured-grid, multi-scale, multi-phase ocean modeling system that can simulate 3D baroclinic circulation, sediment transport, water quality, and biogeochemistry. With Rompy, you can configure SCHISM simulations using Python objects that are validated with Pydantic, ensuring consistent and reproducible model setups.

## Detailed Documentation

For comprehensive documentation on using SCHISM with Rompy, visit: https://rom-py.github.io/rompy-schism

## Worked Examples

For practical, hands-on examples of how to use SCHISM with Rompy, please see the following notebook:

- **[SCHISM Demo](notebooks/schism/schism_demo.ipynb)**: A basic demonstration of a SCHISM run.

## Next Steps

- Review the [Backends Guide](backends.md) for detailed execution options
- Learn about [Configuration Deep Dive](configuration_deep_dive.md) for detailed configuration options
- Check the [Progressive Tutorials](progressive_tutorials.md) for practical examples