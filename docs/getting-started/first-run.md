# Your first run

This page goes through a complete rompy run without any model installed. It uses rompy's built-in base configuration, whose template writes a small text file, so every step works the same way as with a real model plugin but the output is short enough to read. Every Python block on this page is executed when the docs are built.

```python exec="on" session="first-run"
# Hidden setup: quiet logging and a temporary output folder.
import tempfile

from rompy.logging import config as logging_config

logging_config.update(level="WARNING")
OUT_DIR = tempfile.mkdtemp()
```

## 1. The run period

A [`TimeRange`][rompy.core.time.TimeRange] defines when the model runs and the interval of its time steps or outputs. See [Time](../concepts/time.md).

```python exec="on" source="above" result="text" session="first-run"
from rompy.core.time import TimeRange

period = TimeRange(start="2023-01-01T00", end="2023-01-02T00", interval="6h")
for time in period.date_range:
    print(time)
```

## 2. The configuration

The configuration describes the model. With a plugin it is the plugin's config class, such as `rompy_xbeach.config.Config`; here it is rompy's [`BaseConfig`][rompy.core.config.BaseConfig]. Its only fields say where its template is (`checkout` is the branch used when the template is a git repository):

```python exec="on" source="above" result="text" session="first-run"
from pathlib import Path

from rompy.core.config import BaseConfig

config = BaseConfig()
print(config.model_type)
print("/".join(Path(config.template).parts[-3:]), config.checkout)
```

`model_type` is the tag that identifies the configuration class. Each plugin registers its own (`xbeach`, `swan`, `schism`), and `ModelRun` uses the tag to pick the right class when it reads a configuration from YAML.

## 3. The model run

[`ModelRun`][rompy.model.ModelRun] joins the configuration with the period, a run id and an output directory:

```python exec="on" source="above" result="text" session="first-run"
from rompy.model import ModelRun

run = ModelRun(run_id="first_run", period=period, output_dir=OUT_DIR, config=config)
print(run.run_id, run.period.start, run.period.end)
```

## 4. Generate the workspace

Calling the run (or [`ModelRun.generate`][rompy.model.ModelRun.generate]) writes the model's input files into `output_dir/run_id` and returns that folder:

```python exec="on" source="above" result="text" session="first-run"
workspace = Path(run())
for path in sorted(workspace.rglob("*")):
    print(path.relative_to(workspace))
```

Generation works in two steps. `ModelRun` calls the configuration with itself (a plugin uses this step to extract data and write its files), then calls the configuration's `render` method with a context holding the run (`runtime`) and the configuration (`config`). `BaseConfig.render` renders a [cookiecutter](https://cookiecutter.readthedocs.io/) template with that context. The base template writes one file, `INPUT`, from the run period (its `$` header lines, which record who generated it and when, are left out here):

```python exec="on" source="above" result="text" session="first-run"
text = (workspace / "INPUT").read_text()
print("\n".join(line for line in text.splitlines() if line and not line.startswith("$")))
```

A model plugin writes the model's own files instead: `params.txt` for XBeach, the `INPUT` command file for SWAN, namelists for SCHISM. [Templates and rendering](../concepts/templates.md) explains the mechanism.

## 5. Run it

A backend runs a command in the workspace. [`LocalConfig`][rompy.backends.config.LocalConfig] runs it on this machine. There is no model here, so the command only reads the generated file, as a model would, and writes a log:

```python exec="on" source="above" result="text" session="first-run"
from rompy.backends import LocalConfig

backend = LocalConfig(command="grep compute INPUT > run.log", timeout=60)
success = run.run(backend, workspace_dir=workspace)
print("success:", success)
print((workspace / "run.log").read_text())
```

With a real model the command is the model executable, for example `LocalConfig(command="xbeach")`, or a container through [`DockerConfig`][rompy.backends.config.DockerConfig]. See [Backends](../concepts/backends.md). Passing `workspace_dir` runs the workspace already generated; without it, the local backend generates it first.

## 6. The same run as YAML

The run can be written as a YAML file. Loading it builds the same objects and applies the same checks; `model_type: base` selects the configuration class:

```python exec="on" source="above" result="text" session="first-run"
import yaml

text = """
run_id: first_run
output_dir: simulations
period:
  start: 2023-01-01T00:00
  end: 2023-01-02T00:00
  interval: 6h
config:
  model_type: base
"""

run_from_yaml = ModelRun(**yaml.safe_load(text))
print(type(run_from_yaml.config).__name__)
print(run_from_yaml.period.date_range == run.period.date_range)
```

From the command line, `rompy generate` writes the workspace from such a file and `rompy run` also runs it, with the backend in its own file:

```bash
rompy generate first_run.yml
rompy run first_run.yml --backend-config local.yml
```

```yaml title="local.yml"
type: local
command: grep compute INPUT > run.log
```

See [the command line](../how-to/cli.md) and [YAML configurations](../how-to/yaml.md).

## Next steps

- The [rompy hands-on notebook](https://rom-py.github.io/rompy-notebooks/notebooks/common/rompy_hands_on/) builds a toy model plugin with a grid and input data, and runs it.
- Build a real model: [your first XBeach model](https://rom-py.github.io/rompy-xbeach/getting-started/first-model/), or the getting-started pages on the [rompy-swan](https://rom-py.github.io/rompy-swan/) and [rompy-schism](https://rom-py.github.io/rompy-schism/) sites.
- Read [Why rompy](../concepts/why-rompy.md) and the concept pages for the ideas behind each step.
