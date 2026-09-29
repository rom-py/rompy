# Writing a model plugin

A model plugin teaches rompy one model. It is a Python package that provides a configuration class, the templates for the model's input files and, usually, grids and data interfaces for the model's own formats. rompy-xbeach, rompy-swan and rompy-schism are model plugins. This page describes the contract they follow, as the code defines it, and builds a small plugin that runs on this page.

## What rompy expects

[`ModelRun.generate`][rompy.model.ModelRun.generate] is the only place rompy calls into a model plugin. It does three things:

1. builds the `runtime` context: the `ModelRun` dumped to a dictionary, plus `staging_dir` (the workspace, `output_dir/run_id`), `_generated_at`, `_generated_on`, `_generated_by` and `_datefmt`;
2. builds the `config` context: `config(run)` if the configuration is callable, otherwise the configuration itself;
3. calls `config.render(context, output_dir)` with `context = {"runtime": ..., "config": ...}`.

A plugin therefore controls generation through three members of its configuration class:

| Member | Default in [`BaseConfig`][rompy.core.config.BaseConfig] | Override it to |
|---|---|---|
| `model_type` | `Literal["base"]` | name the model; every plugin sets its own value |
| `__call__(self, runtime)` | returns `self` | write input files and return what the template needs |
| `render(self, context, output_dir)` | renders the cookiecutter `template` (checked out at `checkout` if it is a git repository) | write the files some other way |

`runtime` in `__call__` is the `ModelRun` itself, so it has `runtime.period`, `runtime.staging_dir` and the other fields. In the template, `runtime` is the dictionary built in step 1.

## The configuration class

Subclass [`BaseConfig`][rompy.core.config.BaseConfig], give it a `model_type` literal, and declare the model's settings as typed pydantic fields:

```python
from pathlib import Path
from typing import Literal

from pydantic import Field
from rompy.core.config import BaseConfig

HERE = Path(__file__).parent


class Config(BaseConfig):
    """Configuration of MyModel."""

    model_type: Literal["mymodel"] = Field("mymodel", description="Model type discriminator")
    template: str = Field(default=str(HERE / "templates" / "mymodel"), description="The model template")
    dt: float = Field(60.0, gt=0, description="Time step (s)")
```

- **`model_type`** is how `ModelRun` picks this class out of YAML (see [discriminated unions](architecture.md#how-the-class-is-picked-discriminated-unions)). Use a short, lower-case name, the same as the entry-point name.
- **Fields are validated when the object is built.** [`RompyBaseModel`][rompy.core.types.RompyBaseModel], the base of `BaseConfig`, forbids unknown fields and suggests the closest name for a typo, so a misspelt setting fails straight away instead of being ignored.
- **Point `template` at the package's template** by default, so users never have to set it.
- `BaseConfig` has no `grid` or data fields. The plugin adds the ones its model needs.

## The template

The default `render` uses [cookiecutter](https://cookiecutter.readthedocs.io/) with rompy's changes: no `cookiecutter.json` is needed, and the template directory holds one folder named `{{runtime.staging_dir}}`. Everything inside that folder is copied into the workspace, and every file is rendered with Jinja2 using the context:

```text
templates/mymodel/
├── __init__.py                 (optional, so the template ships with the package)
└── {{runtime.staging_dir}}/
    ├── mymodel.inp             rendered with {{ config.* }} and {{ runtime.* }}
    └── outputs/                folders are created in the workspace too
```

The variables available in a template are `config` (whatever `__call__` returned), `runtime` (the dictionary described above) and `_template` (the path of the template used). rompy's own [base template](https://github.com/rom-py/rompy/tree/main/src/rompy/templates/base) is a minimal example. [Templates and rendering](../concepts/templates.md) explains the mechanism in more detail.

## Worked example

The [rompy hands-on notebook](https://rom-py.github.io/rompy-notebooks/notebooks/common/rompy_hands_on/) builds a similar toy plugin step by step. This plugin describes a toy model that reads a time step, a number of steps and a friction file. The page writes the template to a temporary folder; in a package it would live under `src/<package>/templates/`.

```python exec="on" session="model-plugin"
# Hidden setup: quiet logging and a temporary folder.
import tempfile
from pathlib import Path

from rompy.logging import config as logging_config

logging_config.update(level="WARNING")
TMP = Path(tempfile.mkdtemp())
```

First, the template: one input file that uses both `runtime` and `config`.

```python exec="on" source="above" session="model-plugin"
template = TMP / "toy_template"
workspace = template / "{{runtime.staging_dir}}"
workspace.mkdir(parents=True)
(workspace / "toy.inp").write_text(
    "! Toy model input, generated by rompy\n"
    "run_id = {{ runtime.run_id }}\n"
    "start = {{ runtime.period.start.strftime('%Y-%m-%dT%H:%M') }}\n"
    "dt = {{ config.dt }}\n"
    "nsteps = {{ config.nsteps }}\n"
    "frictionfile = {{ config.frictionfile }}\n"
)
```

Then the configuration class. `__call__` does the model-specific work: it derives the number of steps from the run period, writes the friction file into the workspace, and returns the values the template uses.

```python exec="on" source="above" session="model-plugin"
from pydantic import Field
from rompy.core.config import BaseConfig


class ToyConfig(BaseConfig):
    """Configuration of the toy model."""

    # A real plugin also declares: model_type: Literal["toy"] = "toy"
    template: str = Field(default=str(template), description="The model template")
    dt: float = Field(60.0, gt=0, description="Time step (s)")
    friction: float = Field(0.02, ge=0, description="Manning coefficient")

    def __call__(self, runtime) -> dict:
        duration = (runtime.period.end - runtime.period.start).total_seconds()
        friction_file = Path(runtime.staging_dir) / "friction.txt"
        friction_file.write_text(f"{self.friction}\n")
        return {
            "dt": self.dt,
            "nsteps": int(duration // self.dt),
            "frictionfile": friction_file.name,
        }
```

The fields are checked like those of any plugin:

```python exec="on" source="above" result="text" session="model-plugin"
for settings in [{"dt": -1}, {"fricton": 0.03}]:
    try:
        ToyConfig(**settings)
    except Exception as err:
        print(err, end="\n\n")
```

Generating a workspace runs `__call__` and renders the template:

```python exec="on" source="above" result="text" session="model-plugin"
from rompy.core.time import TimeRange
from rompy.model import ModelRun

run = ModelRun(
    run_id="toy",
    period=TimeRange(start="2023-01-01T00", end="2023-01-01T06", interval="1h"),
    output_dir=TMP / "runs",
    config=ToyConfig(dt=300),
)
staging_dir = run.generate()

print(sorted(path.name for path in staging_dir.iterdir()))
print((staging_dir / "toy.inp").read_text())
```

## Overriding `render`

Some models are easier to write without a template, for example when a library already writes the input files. Override `render` and write into the workspace, which is `context["runtime"]["staging_dir"]`. The `output_dir` argument is the `ModelRun.output_dir`, the parent of the workspace.

```python exec="on" source="above" result="text" session="model-plugin"
class ToyDirectConfig(ToyConfig):
    """The toy model, written without a template."""

    def render(self, context: dict, output_dir) -> None:
        values = context["config"]  # what __call__ returned
        workspace = Path(context["runtime"]["staging_dir"])
        lines = [f"{key} = {value}" for key, value in values.items()]
        (workspace / "toy.inp").write_text("\n".join(lines) + "\n")


run = ModelRun(run_id="direct", period=run.period, output_dir=TMP / "runs", config=ToyDirectConfig())
staging_dir = run.generate()
print((staging_dir / "toy.inp").read_text())
```

## Trying a plugin before registering it

`ModelRun.config` accepts only the configuration types installed in the `rompy.config` entry-point group (see [how rompy loads plugins](architecture.md#how-rompy-loads-plugins)). A class defined in a script or notebook with a new `model_type` is rejected until its package is installed:

```python exec="on" source="above" result="text" session="model-plugin"
from typing import Literal


class UnregisteredConfig(BaseConfig):
    model_type: Literal["toy"] = "toy"


try:
    ModelRun(config=UnregisteredConfig())
except Exception as err:
    print(err)
```

That is why `ToyConfig` above keeps the inherited `model_type = "base"`: `ModelRun` accepts it as a `BaseConfig`. rompy's own tests use the same approach (`DemoConfig` in `tests/test_helpers.py`). It is enough to develop `__call__`, the template and `render`, but the class is still validated and serialised as a `BaseConfig`, so its own fields are left out of `model_dump()` and of YAML:

```python exec="on" source="above" result="text" session="model-plugin"
print(run.model_dump()["config"])
```

For YAML configurations and the CLI, register the class and install the package, in editable mode while developing (`pip install -e .`).

## Registering the plugin

Add the configuration class to the `rompy.config` group in `pyproject.toml`:

```toml
[project.entry-points."rompy.config"]
toy = "rompy_toy.config:ToyConfig"
```

After `pip install -e .`, `ModelRun(config={"model_type": "toy", ...})` builds a `ToyConfig`, and a YAML file with `model_type: toy` loads with `rompy generate`. `rompy schema rompy_toy.config.ToyConfig` prints its JSON schema.

## Grids and data interfaces

Most plugins also need a grid and data interfaces. rompy provides the base classes; the plugin adds what its model's files need.

**Grids.** Subclass [`BaseGrid`][rompy.core.grid.BaseGrid] (or [`RegularGrid`][rompy.core.grid.RegularGrid]) and implement the `x` and `y` properties. `BaseGrid` then provides `bbox()`, `boundary()` and `plot()`, and the data objects use `bbox()` to crop their sources to the model domain. rompy's grids are told apart by a `grid_type` literal, which a plugin grid should set to its own value.

**Data interfaces.** Subclass the data object that matches the input:

| Base class | Use it for | Its `get` |
|---|---|---|
| [`DataBlob`][rompy.core.data.DataBlob] | Files used as they are, from a local path or a remote URI | `get(destdir, name=None)` copies or links the file and returns its path |
| [`DataPoint`][rompy.core.data.DataPoint] | Time series from a source | `get(destdir, grid=None, time=None)` crops to the period and writes netCDF |
| [`DataGrid`][rompy.core.data.DataGrid] | Gridded data from a source | the same, also cropping to the grid's bounding box plus `buffer` |

A plugin overrides `get` to write the model's own format and, usually, to return the parameters that point to the file. The configuration's `__call__` calls each data interface with `runtime.staging_dir`, the grid and `runtime.period`.

## Running the model

Plugins do not need code to run the model: the [backends](extending.md#run-backends) run a command in the workspace, and a plugin documents that command (for example the XBeach executable) and publishes a Docker image. One optional hook exists: with a [`LocalConfig`][rompy.backends.config.LocalConfig] that has no `command`, the local backend calls `config.run(model_run)` in the workspace if the configuration defines it, and treats a `False` return as a failure.

## How the model plugins do it

| | rompy-xbeach | rompy-swan | rompy-schism |
|---|---|---|---|
| Configuration | `Config`, `model_type: xbeach` | `SwanConfig`, `model_type: swan` (and `SwanConfigComponents`, `swanconfig`) | `SCHISMConfig`, `model_type: schism` |
| `__call__` returns | a flat dict of XBeach parameters, after the data interfaces write their files | a dict of rendered SWAN command blocks (`cgrid`, `inpgrid`, `boundary`, `physics`, ...) | the workspace path; the grid, forcing and namelists are written inside `__call__` |
| Template | `params.txt`, a loop over the parameters | `INPUT`, one slot per command block | folders only (`outputs`, `sflux`, ...) |
| Grid | `RegularGrid(BaseGrid)`, told apart by `model_type` | `SwanGrid(RegularGrid)`, `grid_type: REG` or `CURV` | `SCHISMGrid(BaseGrid)`, `grid_type: schism` |
| Data interfaces | `BaseData(DataGrid)` subclasses for bathymetry, waves, wind and tide, in its own `xbeach.data` group | `SwanDataGrid(DataGrid)`; boundaries from `BoundaryWaveStation` | `SfluxSource(DataGrid)` and others; `DataBlob` for files |
| Docs and code | [docs](https://rom-py.github.io/rompy-xbeach/), [How rompy-xbeach works](https://rom-py.github.io/rompy-xbeach/user-guide/how-it-works/), [code](https://github.com/rom-py/rompy-xbeach) | [docs](https://rom-py.github.io/rompy-swan/), [code](https://github.com/rom-py/rompy-swan) | [docs](https://rom-py.github.io/rompy-schism/), [code](https://github.com/rom-py/rompy-schism) |

The three show the range of the contract: rompy-xbeach and rompy-swan compute values in `__call__` and let the template lay them out, while rompy-schism writes the files itself and uses the template only for the folder structure.

## A plugin package

```text
rompy-toy/
├── pyproject.toml              entry points: rompy.config, plus any groups of your own
├── src/rompy_toy/
│   ├── config.py               ToyConfig(BaseConfig)
│   ├── grid.py                 ToyGrid(BaseGrid)
│   ├── data.py                 data interfaces (DataGrid, DataBlob subclasses)
│   ├── components/             groups of model settings, if the model has many
│   └── templates/toy/{{runtime.staging_dir}}/...
├── tests/
└── docs/                       see Documenting a plugin
```

Include the templates as package data (rompy-xbeach sets `[tool.setuptools.package-data] "*" = ["*.*"]`), otherwise an installed package cannot find them. [Documenting a plugin](documenting.md) describes the docs site every model plugin shares.
