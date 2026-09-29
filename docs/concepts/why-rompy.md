# Why rompy

Setting up an ocean or coastal model involves the same chores whatever the model:

- define where the model is (a grid) and when it runs (a period);
- turn bathymetry, wind, waves and water levels from datasets in many formats into the model's own input files;
- write the model settings in the model's own format;
- run the model somewhere, and repeat for the next event, site or variant.

Every model does these in its own way: SWAN reads a command file (`INPUT`), XBeach a flat `params.txt` file, SCHISM a set of Fortran namelists. rompy gives the chores one structure in Python, and model plugins such as rompy-swan, rompy-xbeach and rompy-schism fill in what is specific to each model.

## Without and with rompy

| Task | Without rompy | With rompy |
|---|---|---|
| Describe the model | Hand-edited text files. Mistakes surface when the model starts, or not at all. | Python objects that check their values as you build them. rompy writes the text files. |
| Prepare input data | One script per dataset to crop, interpolate and convert. | Data objects that pair a source with the grid and period. rompy extracts only what the run needs. |
| Share and reproduce | Scripts, plus notes on how they were run. | The whole run as one Python object or YAML file, checked again when loaded. |
| Run the model | Shell scripts tied to one machine. | The same workspace, run locally, in Docker or on a cluster by choosing a backend. |
| Try variants | Copy directories and edit them by hand. | Copy the configuration, change one setting, and generate a new workspace. |

## The big picture

A model run in rompy goes through three steps:

```text
  1. Describe                2. Generate                 3. Run (optional)
  ───────────                ───────────                 ─────────────────
  period       when
  grid         where         ModelRun writes the         a backend runs the
  data         forcing   ─▶  model's input files     ─▶  model on the workspace:
  components   settings      and forcing into a          local, Docker,
                             workspace                   a scheduler
  checked as you build them
```

The steps look alike in every model. This is the XBeach version from [your first XBeach model](https://rom-py.github.io/rompy-xbeach/getting-started/first-model/), shortened:

```python
from rompy.backends import DockerConfig
from rompy.core.time import TimeRange
from rompy.model import ModelRun
from rompy_xbeach.config import Config

period = TimeRange(start="2023-01-01T00:00", end="2023-01-01T00:30", interval="10m")
config = Config(grid=grid, bathy=bathy, input=forcing, physics=physics)  # 1. describe

run = ModelRun(run_id="first_model", period=period, output_dir="runs", config=config)
workspace = run()  # 2. generate: params.txt, bathymetry and boundary files

backend = DockerConfig(image="ghcr.io/rom-py/xbeach", executable="xbeach")
run.run(backend, workspace_dir=workspace)  # 3. run XBeach in Docker
```

rompy provides [`TimeRange`][rompy.core.time.TimeRange], [`ModelRun`][rompy.model.ModelRun], the data sources and the backends. The plugin provides `Config` and everything inside it. [Your first run](../getting-started/first-run.md) goes through the same steps with no model installed.

## Four ideas

1. **The model is described by checked objects, in Python or YAML.** Each setting is a typed field with its allowed values, and plugins add the model's own rules, such as which wave boundary types a wave model accepts. The same description can be written in Python or as a YAML file. See [Configuration and validation](configuration.md).
2. **Input data is a request, not a copy.** A data object names a source, the variables and how to read them. rompy selects the part that covers the grid and period, and writes it in the form the model needs. See [Data and sources](data.md).
3. **Describing, generating and running are separate steps.** You can check a configuration and inspect the generated files before a model executable is involved, and run the same workspace on different machines. See [The run lifecycle](run-lifecycle.md) and [Backends](backends.md).
4. **A small core with plugins.** Models, data sources, run backends and file transfers are plugins registered through Python entry points, so each can grow without changing the others.

## The same ideas in each model

| | SWAN | XBeach | SCHISM |
|---|---|---|---|
| Plugin | [rompy-swan](https://rom-py.github.io/rompy-swan/) | [rompy-xbeach](https://rom-py.github.io/rompy-xbeach/) | [rompy-schism](https://rom-py.github.io/rompy-schism/) |
| Configuration | `SwanConfig` | `Config` | `SCHISMConfig` |
| Grid | `SwanGrid`, regular | `RegularGrid`, regular and rotated | `SCHISMGrid`, unstructured mesh |
| Forcing data | `SwanDataGrid`, boundary classes such as `Boundnest1` | `XBeachBathy`, wave boundary classes, `WindGrid`, `TideConsGrid` | `SCHISMData`: atmospheric, ocean, tidal and wave forcing |
| Files rompy writes | the `INPUT` command file | `params.txt` | namelists such as `param.nml` |

The grid and data classes of each plugin extend rompy's, described in [Grids](grids.md) and [Data and sources](data.md). [How rompy-xbeach works](https://rom-py.github.io/rompy-xbeach/user-guide/how-it-works/) shows the mapping for one model in detail.

## What stays with the modeller

rompy checks that a configuration is complete and consistent, and does the repetitive work. It does not decide whether a dataset suits the question, whether the settings are physically sensible, or whether the model results are right. Look at the generated inputs and outputs, and validate the model against observations as you would without rompy.

## Where next

- Try it: [your first run](../getting-started/first-run.md) on this site, then the [rompy hands-on notebook](https://rom-py.github.io/rompy-notebooks/notebooks/common/rompy_hands_on/), which builds and runs a toy model plugin.
- Read the concept pages: [Configuration and validation](configuration.md), [Time](time.md), [Grids](grids.md) and [Data and sources](data.md).
- Go to a model: the tutorials for [SWAN](https://rom-py.github.io/rompy-notebooks/notebooks/swan/tutorial/01_first_model/) and [XBeach](https://rom-py.github.io/rompy-notebooks/notebooks/xbeach/tutorial/01_first_model/), and the [SCHISM notebooks](https://rom-py.github.io/rompy-notebooks/notebooks/schism/tutorial_01_rompy_orientation/).
