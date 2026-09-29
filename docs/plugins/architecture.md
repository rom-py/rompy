# Plugin architecture

rompy keeps a small core and lets plugins add models, data sources, run environments, postprocessing and file transfers. This page explains the plugin types, the entry-point groups that register them, and how rompy loads them.

```text
                          rompy core
      ModelRun · TimeRange · grids · data objects · CLI
                               │
   ┌──────────┬──────────┬─────┴─────┬──────────────┬──────────┐
 model      source     backend   postprocessor   pipeline    transfer
 plugins    plugins    plugins   plugins         plugins     plugins
 XBeach,    files,     local,    output checks,  generate →  file, http,
 SWAN,      intake,    Docker,   analysis        run →       s3, gs, az,
 SCHISM     Datamesh   Slurm                     postprocess oceanum
```

## The plugin types

| Plugin type | What it provides | Base class | Guide |
|---|---|---|---|
| Model | The configuration of one model: its settings, grid, forcing and templates | [`BaseConfig`][rompy.core.config.BaseConfig] | [Writing a model plugin](model-plugin.md) |
| Source | A way to open a dataset as xarray | [`SourceBase`][rompy.core.source.SourceBase] | [Sources](extending.md#sources) |
| Run backend | Where and how a generated workspace runs | [`BaseBackendConfig`][rompy.backends.config.BaseBackendConfig] plus a backend class | [Run backends](extending.md#run-backends) |
| Postprocessor | What happens to the outputs after a run | [`BasePostprocessorConfig`][rompy.postprocess.config.BasePostprocessorConfig] plus a processor class | [Postprocessors](extending.md#postprocessors) |
| Pipeline | The order of generate, run and postprocess | a class with `execute()` | [Pipelines](extending.md#pipeline-backends) |
| Transfer | Copying files from and to a URI scheme | [`TransferBase`][rompy.transfer.base.TransferBase] | [Transfers](extending.md#transfers) |

The split lets each part change on its own:

- model plugins are released separately from rompy, so a model can gain features without a rompy release;
- a data source can be swapped without touching the model configuration;
- the same workspace can run locally, in Docker or on a cluster by changing only the backend.

A plugin boundary is an extension point, not a promise that every plugin supports every source or workflow. The model plugin's documentation says which sources and forcing types it accepts.

## Entry-point groups

Plugins register their classes as [Python entry points](https://packaging.python.org/en/latest/specifications/entry-points/) in their `pyproject.toml`. Installing the package is enough for rompy to find them. These are the groups rompy reads, with a real example of each:

| Group | Registers | Example |
|---|---|---|
| `rompy.config` | Model configurations, the classes `ModelRun.config` accepts | rompy: `base = "rompy.core.config:BaseConfig"`<br>rompy-xbeach: `xbeach = "rompy_xbeach.config:Config"` |
| `rompy.source` | Sources accepted by rompy's data objects | rompy: `file = "rompy.core.source:SourceFile"`, `"csv:timeseries" = "rompy.core.source:SourceTimeseriesCSV"` |
| `rompy.run` | Run backend classes | rompy: `local = "rompy.run:LocalRunBackend"`, `docker = "rompy.run.docker:DockerRunBackend"` |
| `rompy.postprocess` | Postprocessor classes | rompy: `noop = "rompy.postprocess:NoopPostprocessor"` |
| `rompy.postprocess.config` | Postprocessor configurations, loaded from a file by their `type` | rompy: `noop = "rompy.postprocess.config:NoopPostprocessorConfig"` |
| `rompy.pipeline` | Pipeline backends | rompy: `local = "rompy.pipeline:LocalPipelineBackend"` |
| `rompy.transfer` | Transfer classes, one entry per URI scheme | rompy: `file`, `http`, `https`, `oceanum`, `s3`, `gs`, `az`, e.g. `s3 = "rompy.transfer.cloud:CloudTransfer"` |

The model packages register their configurations in `rompy.config`:

| Package | `rompy.config` entries |
|---|---|
| rompy-xbeach | `xbeach = "rompy_xbeach.config:Config"` |
| rompy-swan | `swan = "rompy_swan.config:SwanConfig"`, `swan_components = "rompy_swan.config:SwanConfigComponents"` |
| rompy-schism | `schism = "rompy_schism.config:SCHISMConfig"`, `schismcsiro = "rompy_schism.config:SchismCSIROConfig"` |

A plugin can also define groups of its own, for its own extension points. rompy-xbeach does this:

```toml
[project.entry-points."xbeach.data"]            # forcing data interfaces, tagged by kind
"wind_grid:wind" = "rompy_xbeach.data.wind:WindGrid"
"water_level_grid:tide" = "rompy_xbeach.data.waterlevel:WaterLevelGrid"
"params:wave" = "rompy_xbeach.data.boundary:BoundaryParams"

[project.entry-points."xbeach.source"]          # sources that carry a coordinate reference system
"geotiff:crs" = "rompy_xbeach.source:SourceGeotiff"

[project.entry-points."xbeach.interpolator"]    # interpolators for the bathymetry
regular_grid = "rompy_xbeach.interpolate:RegularGridInterpolator"
```

The text after the colon in an entry-point name is a tag. `load_entry_points("xbeach.data", etype="wind")` returns only the entries tagged `wind`, which is how rompy-xbeach builds the list of accepted wind inputs. rompy uses the same convention: its `DataPoint` accepts only the sources tagged `timeseries`.

## How rompy loads plugins

`rompy.utils.load_entry_points(group, etype=None)` returns the classes registered in a group as a tuple, optionally filtered by tag. rompy calls it when its modules are imported:

| Where | What it builds |
|---|---|
| `rompy.model` | `CONFIG_TYPES` from `rompy.config`, the classes accepted by [`ModelRun.config`][rompy.model.ModelRun]; and the lists of run, postprocessor and pipeline backends |
| `rompy.core.data` | The sources accepted by [`DataGrid.source`][rompy.core.data.DataGrid] (all of `rompy.source`) and [`DataPoint.source`][rompy.core.data.DataPoint] (those tagged `timeseries`) |
| `rompy.core.boundary` | The sources accepted by [`BoundaryWaveStation`][rompy.core.boundary.BoundaryWaveStation] |
| `rompy.transfer.registry` | A scheme → class table from `rompy.transfer`, built on first use by [`get_transfer`][rompy.transfer.registry.get_transfer] |

Because the lists are built at import time, a plugin must be installed (its entry points present in the environment's package metadata) before rompy is imported. A class defined in a script or notebook is not in these lists; [Writing a model plugin](model-plugin.md#trying-a-plugin-before-registering-it) shows what that means in practice.

The installed model types are visible from Python:

```python exec="on" source="above" result="text" session="architecture"
from rompy.model import CONFIG_TYPES

for cls in CONFIG_TYPES:
    print(f"{cls.model_fields['model_type'].default!r:10} {cls.__module__}.{cls.__name__}")
```

## How the class is picked: discriminated unions

`ModelRun.config` is declared as a union of the registered classes, discriminated by their `model_type` field:

```python
config: Union[CONFIG_TYPES] = Field(default_factory=BaseConfig, discriminator="model_type")
```

Each configuration class declares `model_type` as a `Literal`, e.g. `model_type: Literal["xbeach"] = "xbeach"`. When a `ModelRun` is built from a dictionary or YAML, pydantic reads `model_type` and validates the rest against that one class. The error for an unknown value lists the values that are installed:

```python exec="on" source="above" result="text" session="architecture"
from rompy.model import ModelRun

try:
    ModelRun(run_id="test", config={"model_type": "not-a-model"})
except Exception as err:
    print(err)
```

Two details matter when writing a plugin:

- **The discriminator is `model_type`, not the entry-point name.** rompy-swan registers `swan_components`, but that class is selected in YAML with `model_type: swanconfig`. Keep the two equal when you can.
- **The same pattern runs through the whole tree.** Sources are told apart by `model_type`, rompy's grids by `grid_type`, and plugins use `model_type` for their own variants (wave boundaries, friction formulations and so on). A YAML file therefore names every class it uses, and round-trips back to the same objects.

Run backends and postprocessors are chosen differently: you pass a configuration object, such as [`DockerConfig`][rompy.backends.config.DockerConfig], to [`ModelRun.run`][rompy.model.ModelRun.run], and the object names the class that runs it. The run environment then stays out of the model configuration, so the same model can run anywhere. See [Writing sources, backends and postprocessors](extending.md).

## See it in the notebooks

- [How the pieces fit together](https://rom-py.github.io/rompy-notebooks/notebooks/xbeach/tutorial/01_first_model/#how-the-pieces-fit-together) in the first XBeach tutorial shows which objects come from rompy and which from rompy-xbeach.
- [Data sources](https://rom-py.github.io/rompy-notebooks/notebooks/xbeach/examples/data_sources/) uses sources from both rompy and rompy-xbeach.
- [Running XBeach](https://rom-py.github.io/rompy-notebooks/notebooks/xbeach/examples/running_xbeach/) and [Running SWAN](https://rom-py.github.io/rompy-notebooks/notebooks/swan/examples/running_swan/) run the same kind of workspace locally, in Docker and with MPI.
