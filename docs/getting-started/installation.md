# Installation

A working setup has three layers: rompy itself, a plugin for each model you want to configure, and the model executable that runs the generated workspace. Only rompy is needed to follow the concept pages; a plugin is needed to build a real model; the executable (or Docker) is needed only to run it.

## rompy

rompy needs Python 3.10 or later.

```bash
pip install rompy
```

To follow the development version, install from GitHub:

```bash
pip install "rompy @ git+https://github.com/rom-py/rompy.git"
```

### Optional extras

| Extra | Adds | Needed for |
|---|---|---|
| `extra` | gcsfs, zarr, cloudpathlib with the S3, GCS and Azure clients | Reading and writing cloud storage (`s3://`, `gs://`, `az://`) and zarr stores |
| `test` | pytest, envyaml, coverage | Running the test suite |
| `dev` | the `test` packages plus ruff, black and respx | Development |
| `docs` | rompy-docs, mkdocs-jupyter | Building these docs |

```bash
pip install "rompy[extra]"
```

## Model plugins

Each model has its own plugin package. Installing a plugin installs rompy as a dependency and registers the model with it, so `ModelRun` and YAML files recognise its `model_type`.

| Model | Package | Documentation |
|---|---|---|
| XBeach | `pip install rompy-xbeach` | [rom-py.github.io/rompy-xbeach](https://rom-py.github.io/rompy-xbeach/) |
| SWAN | `pip install rompy-swan` | [rom-py.github.io/rompy-swan](https://rom-py.github.io/rompy-swan/) |
| SCHISM | `pip install rompy-schism` | [rom-py.github.io/rompy-schism](https://rom-py.github.io/rompy-schism/) |

Several plugins can be installed in the same environment.

## Model executables

rompy and the plugins write model workspaces; they do not include the models. To run a model you need either the executable installed locally or Docker.

- **XBeach**: the public Docker image `ghcr.io/rom-py/xbeach` contains XBeach built with NetCDF output. The [rompy-xbeach docs](https://rom-py.github.io/rompy-xbeach/) list its tags and how to use your own build.
- **SWAN** and **SCHISM**: how to install or containerise the executable is documented on the [rompy-swan](https://rom-py.github.io/rompy-swan/) and [rompy-schism](https://rom-py.github.io/rompy-schism/) sites.

rompy runs the model through a backend: [`LocalConfig`][rompy.backends.config.LocalConfig] for an executable on your machine, [`DockerConfig`][rompy.backends.config.DockerConfig] for a container and [`SlurmConfig`][rompy.backends.config.SlurmConfig] for a cluster.

## Check the installation

This prints the installed version of rompy and of each plugin:

```python
from importlib.metadata import PackageNotFoundError, version

for package in ["rompy", "rompy-xbeach", "rompy-swan", "rompy-schism"]:
    try:
        print(f"{package:14s} {version(package)}")
    except PackageNotFoundError:
        print(f"{package:14s} not installed")
```

The `rompy` command prints the rompy version and the model types registered by the installed plugins:

```bash
rompy --version
```

Next: [Your first run](first-run.md).
