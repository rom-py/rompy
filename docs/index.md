# rompy

rompy (Relocatable Ocean Modelling in PYthon) sets up and runs ocean and coastal models from Python or YAML. You describe a model run as validated objects: when it runs, where, which data force it and how the model is configured. rompy then writes the model's input files into a workspace and runs the model on it, locally, in Docker or on a cluster.

Every model reads its inputs in its own format, but the chores are the same: define a period and a grid, turn datasets into forcing files, write the settings, run the model and repeat for the next event or variant. rompy provides the parts every model shares: the model run and its period, grids, data sources and the objects that extract data for a run, templates, run backends and the `rompy` command. Model plugins add the rest for one model each.

Because the whole run is one object, it can be checked before the model starts, saved as a YAML file, and generated again on another machine or with one setting changed.

## A first look

This example uses rompy's built-in base configuration, which needs no model, and writes a workspace from a template:

```python exec="on" session="index"
# Hidden setup: quiet logging and a temporary output folder.
import tempfile

from rompy.logging import config as logging_config

logging_config.update(level="WARNING")
OUT_DIR = tempfile.mkdtemp()
```

```python exec="on" source="above" result="text" session="index"
from rompy.core.config import BaseConfig
from rompy.core.time import TimeRange
from rompy.model import ModelRun

run = ModelRun(
    run_id="first_run",
    period=TimeRange(start="2023-01-01T00", end="2023-01-02T00", interval="1h"),
    output_dir=OUT_DIR,
    config=BaseConfig(),
)
workspace = run.generate()

print(sorted(path.name for path in workspace.iterdir()))
for line in (workspace / "INPUT").read_text().splitlines():
    if not line.startswith("$"):  # skip the header comments
        print(line)
```

With a model plugin, `config` is the model's configuration, such as rompy-xbeach's `Config`, and the workspace holds that model's input files. [Your first run](getting-started/first-run.md) goes through these steps in detail.

## The model family

| Package | What it does | Documentation |
|---|---|---|
| rompy | The framework: model runs, time, grids, data and sources, templates, backends, the CLI | this site |
| rompy-xbeach | [XBeach](https://xbeach.readthedocs.io/): nearshore waves, sediment transport and morphology | [rompy-xbeach](https://rom-py.github.io/rompy-xbeach/) |
| rompy-swan | [SWAN](https://swanmodel.sourceforge.io/): spectral waves in coastal waters | [rompy-swan](https://rom-py.github.io/rompy-swan/) |
| rompy-schism | [SCHISM](https://schism-dev.github.io/schism/master/index.html): unstructured-grid hydrodynamics, with waves through WWM | [rompy-schism](https://rom-py.github.io/rompy-schism/) |
| rompy-notebooks | Tutorials and examples for every model | [rompy-notebooks](https://rom-py.github.io/rompy-notebooks/) |

[Models](models.md) has a section for each model, with its tutorial.

## Where to go next

| If you want to | Go to |
|---|---|
| Install rompy and a model plugin | [Installation](getting-started/installation.md) |
| Generate a first workspace, step by step | [Your first run](getting-started/first-run.md) |
| Understand the ideas behind rompy | [Concepts](concepts/why-rompy.md) |
| Use the command line and YAML files | [How-to guides](how-to/cli.md) |
| Add a model, a data source or a backend | [Plugins](plugins/architecture.md) |
| Choose a model and find its documentation | [Models](models.md) |
| Look up a class or function | [Reference](reference/index.md) |
| Learn with notebooks | The [notebook site](https://rom-py.github.io/rompy-notebooks/), starting with the [rompy hands-on notebook](https://rom-py.github.io/rompy-notebooks/notebooks/common/rompy_hands_on/) |
