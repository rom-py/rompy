# Models

Each model is supported by a plugin package with its own documentation site: how the model maps to rompy, a guide to its settings, and its API reference. The tutorials and examples for every model are on the [notebook site](https://rom-py.github.io/rompy-notebooks/).

| Model | Plugin | Install | Documentation | Tutorial |
|---|---|---|---|---|
| XBeach | rompy-xbeach | `pip install rompy-xbeach` | [rompy-xbeach](https://rom-py.github.io/rompy-xbeach/) | [XBeach tutorial](https://rom-py.github.io/rompy-notebooks/xbeach-tutorial/) |
| SWAN | rompy-swan | `pip install rompy-swan` | [rompy-swan](https://rom-py.github.io/rompy-swan/) | [SWAN tutorial](https://rom-py.github.io/rompy-notebooks/swan-tutorial/) |
| SCHISM | rompy-schism | `pip install rompy-schism` | [rompy-schism](https://rom-py.github.io/rompy-schism/) | [SCHISM tutorial](https://rom-py.github.io/rompy-notebooks/schism-tutorial/) |

Installing a plugin also installs rompy, and registers the model's configuration so that `ModelRun` and the `rompy` command accept it (see [Plugin architecture](plugins/architecture.md)).

## XBeach

[XBeach](https://xbeach.readthedocs.io/) models nearshore waves, currents, sediment transport and morphological change, for example beach and dune erosion during storms. It reads a flat parameter file, `params.txt`, plus files for the grid, bathymetry and forcing.

rompy-xbeach builds `params.txt` and those files from a configuration with a rotated regular grid, bathymetry interpolated from GeoTIFF, XYZ or gridded data, wave boundaries from parameters, spectra or files, tide, water level and wind forcing, and the physics, sediment and output settings.

- Documentation: [rompy-xbeach](https://rom-py.github.io/rompy-xbeach/), starting with [Your first model](https://rom-py.github.io/rompy-xbeach/getting-started/first-model/) and [How rompy-xbeach works](https://rom-py.github.io/rompy-xbeach/user-guide/how-it-works/)
- Tutorial: [XBeach tutorial](https://rom-py.github.io/rompy-notebooks/xbeach-tutorial/)
- Configuration type: `model_type: xbeach`

## SWAN

[SWAN](https://swanmodel.sourceforge.io/) is a third-generation spectral wave model for coastal regions, lakes and estuaries. It reads a command file, `INPUT`, and input grids for bathymetry, wind and currents.

rompy-swan writes the `INPUT` command file from components that mirror SWAN's commands (computational grid, input grids, boundaries, physics, numerics, output), and writes the input grids and boundary spectra from data sources.

- Documentation: [rompy-swan](https://rom-py.github.io/rompy-swan/)
- Tutorial: [SWAN tutorial](https://rom-py.github.io/rompy-notebooks/swan-tutorial/)
- Configuration types: `model_type: swan`, and `model_type: swanconfig` for `SwanConfigComponents`

## SCHISM

[SCHISM](https://schism-dev.github.io/schism/master/index.html) is a hydrodynamic model on unstructured grids, from the ocean to creeks, with optional modules such as the WWM wave model. It reads a horizontal grid (`hgrid.gr3`), a vertical grid, Fortran namelists (`param.nml` and others) and forcing files.

rompy-schism writes the grids, the namelists, the tidal and ocean boundaries and the atmospheric forcing (`sflux`) from its configuration.

- Documentation: [rompy-schism](https://rom-py.github.io/rompy-schism/)
- Tutorial: [SCHISM tutorial](https://rom-py.github.io/rompy-notebooks/schism-tutorial/)
- Configuration type: `model_type: schism`

## Other models

Any model with text or file inputs can be added as a plugin, for example WAVEWATCH III. A plugin needs a configuration class, templates for the model's input files and, usually, grid and data classes for the model's formats. [Writing a model plugin](plugins/model-plugin.md) describes the contract and builds a small plugin, and [Documenting a plugin](plugins/documenting.md) sets up its documentation site.
