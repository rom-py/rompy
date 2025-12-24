# XBeach Model Guide

## Installation

To use the XBeach model with Rompy, install the dedicated plugin:

```bash
pip install rompy-xbeach
```

## Overview

XBeach is a numerical model for the simulation of nearshore and coastal processes. It is designed to compute wave propagation, sediment transport, and morphological changes in the coastal zone. With Rompy, you can configure XBeach simulations using Python objects that are validated with Pydantic, ensuring consistent and reproducible model setups.

## Detailed Documentation

For comprehensive documentation on using XBeach with Rompy, visit: https://rom-py.github.io/rompy-xbeach

## Worked Examples

For practical, hands-on examples of how to use XBeach with Rompy, please see the following notebooks:

- **[XBeach Procedural Example](notebooks/xbeach/example_procedural.ipynb)**: A basic demonstration of a procedural XBeach run.
- **[XBeach Grid Demo](notebooks/xbeach/grid-demo.ipynb)**: Examples of XBeach grid configuration and usage.
- **[XBeach Bathymetry Demo](notebooks/xbeach/bathy-demo.ipynb)**: Examples of how to set up bathymetry for XBeach models.
- **[XBeach Forcing Demo](notebooks/xbeach/forcing-demo.ipynb)**: Examples of how to set up forcing conditions for XBeach models.
- **[XBeach Output Demo](notebooks/xbeach/output-demo.ipynb)**: Examples of how to configure and process XBeach outputs.

## Next Steps

- Review the [Backends Guide](backends.md) for detailed execution options
- Learn about [Configuration Deep Dive](configuration_deep_dive.md) for detailed configuration options
- Check the [Progressive Tutorials](progressive_tutorials.md) for practical examples