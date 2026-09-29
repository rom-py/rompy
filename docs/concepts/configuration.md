# Configuration and validation

rompy does not treat a model configuration as a block of text. Every object that describes a run, from the run period to a model's physics settings, is a [Pydantic](https://docs.pydantic.dev/) model with typed fields. A configuration is checked as it is built, before rompy writes any model file or a model starts.

```text
typed fields + type constraints + domain rules
                    |
                    v
      validated description (Python or YAML)
                    |
                    v
          model-native input files
```

A model's own input format describes syntax, and often says little while the configuration is being assembled: the model may accept a file and reject a value only when it runs, silently apply a default, or fail with an opaque parser message. In rompy the model files are an output of a description that has already been checked.

```python exec="on" session="configuration"
# Hidden setup: quiet logging.
from rompy.logging import config as logging_config

logging_config.update(level="WARNING")
```

## The base model

Most rompy objects derive from [`RompyBaseModel`][rompy.core.types.RompyBaseModel]. It adds two checks to Pydantic's defaults: unknown fields are rejected (`extra="forbid"`), and a misspelt field name gets a suggestion.

```python exec="on" source="above" result="text" session="configuration"
from pydantic import ValidationError

from rompy.model import ModelRun

try:
    ModelRun(run_idd="storm")
except ValidationError as err:
    print(err.errors()[0]["msg"])
```

A field name that is not close to any real one is still rejected:

```python exec="on" source="above" result="text" session="configuration"
try:
    ModelRun(colour="red")
except ValidationError as err:
    print(err.errors()[0]["loc"], err.errors()[0]["msg"])
```

This matters most for YAML files, where a typo would otherwise leave a setting at its default without any warning.

## Two layers of checks

**Types.** Pydantic checks that each value has the declared type and converts it where that is unambiguous, for example a date string to a `datetime` or `"6h"` to a `timedelta`. A value that cannot be converted is reported with the field it belongs to:

```python exec="on" source="above" result="text" session="configuration"
from rompy.core.grid import RegularGrid

try:
    RegularGrid(x0=0.0, y0=0.0, dx="ten", dy=10.0, nx=20, ny=10)
except ValidationError as err:
    print(err.errors()[0]["loc"], err.errors()[0]["msg"])
```

**Domain rules.** Validators express what the type alone cannot: required combinations of fields, ranges of physical parameters, options that exclude each other. rompy's core objects have a few:

```python exec="on" source="above" result="text" session="configuration"
from rompy.core.time import TimeRange

for build in [
    lambda: TimeRange(start="2023-01-01"),
    lambda: RegularGrid(x0=0.0, y0=0.0, dx=10.0, dy=10.0, nx=20),
]:
    try:
        build()
    except ValidationError as err:
        print(err.errors()[0]["msg"])
```

Model plugins add many more, specific to their model: allowed ranges of each parameter, options that only apply with a given wave model or solver, forcing types a boundary accepts. The model sites list them with each setting, for example the [rompy-xbeach parameter reference](https://rom-py.github.io/rompy-xbeach/reference/parameters/).

## Choosing between alternatives

Where a field accepts one of several classes, the class is chosen by a tag field, `model_type`, which each class fixes to its own value: `base` or `xbeach` for configurations, `file` or `intake` for sources, `grid` or `point` for data objects. Such fields are discriminated unions: Pydantic reads the tag, picks the class, and validates the rest of the input against that class only. Grids carry a similar tag, `grid_type` (`regular` for [`RegularGrid`][rompy.core.grid.RegularGrid], `schism` for the rompy-schism mesh); see [Grids](grids.md).

In Python you usually pass an object, and the tag comes with it. In YAML or a dictionary, the tag is what selects the class:

```python exec="on" source="above" result="text" session="configuration"
from rompy.core.data import DataGrid

wind = DataGrid(
    id="wind",
    source={"model_type": "file", "uri": "tests/data/era5-20230101.nc"},
    variables=["u10", "v10"],
)
print(type(wind.source).__name__)
```

An unknown tag is reported with the tags that are available:

```python exec="on" source="above" result="text" session="configuration"
try:
    DataGrid(id="wind", source={"model_type": "netcdf", "uri": "wind.nc"})
except ValidationError as err:
    print(err.errors()[0]["msg"])
```

The available classes come from Python entry points, so installed plugins extend them. [`ModelRun.config`][rompy.model.ModelRun] accepts every configuration class registered in the `rompy.config` group, `base` from rompy itself and, for example, `xbeach` from rompy-xbeach. The list printed here depends on the plugins installed where these docs were built:

```python exec="on" source="above" result="text" session="configuration"
try:
    ModelRun(config={"model_type": "not_a_model"})
except ValidationError as err:
    print(err.errors()[0]["msg"])
```

Errors inside a nested object are reported with the full path to the field:

```python exec="on" source="above" result="text" session="configuration"
try:
    DataGrid(id="wind", source={"model_type": "file", "url": "wind.nc"})
except ValidationError as err:
    print(err.errors()[0]["loc"], err.errors()[0]["msg"])
```

## One description, in Python or YAML

The objects that describe a run can be built in Python or loaded from YAML or JSON. Both give the same objects and pass through the same checks.

| | Python | YAML |
|---|---|---|
| Period | `TimeRange(...)` | a `period:` mapping |
| Model setup | plugin objects such as `Config(...)` | nested mappings; `model_type` picks between alternatives |
| Reuse | functions and copies of objects | versioned files, `!include` |
| Checking | when each object is built | when the file is loaded |
| Generate and run | `ModelRun` methods | the same methods, or `rompy generate` and `rompy run` |

Python is convenient while you develop a setup; a YAML file is easy to review, version and hand to someone else or to a scheduled job.

`model_dump(mode="json")` turns any object into plain values that YAML or JSON can hold, and loading them back gives an equal object. The base configuration's `template` field is excluded here because it holds an absolute path to rompy's installed template; left out, it takes its default when loaded.

```python exec="on" source="above" result="text" session="configuration"
import yaml

run = ModelRun(
    run_id="storm",
    period=TimeRange(start="2023-01-01", end="2023-01-02", interval="6h"),
    output_dir="simulations",
)
text = yaml.safe_dump(
    run.model_dump(mode="json", exclude={"config": {"template"}}), sort_keys=False
)
print(text)

reloaded = ModelRun(**yaml.safe_load(text))
print("same run:", reloaded.model_dump() == run.model_dump())
```

JSON works the same way with `model_dump_json()` and `ModelRun.model_validate_json()`.

!!! warning "Keep the tags when writing files"
    `model_dump(exclude_defaults=True)` drops the `model_type` and `grid_type` tags, because they are defaults. A file written that way cannot be loaded back where a field accepts several classes. Keep the tags in files you write by hand too.

## Schemas

Because every object is a Pydantic model, its JSON schema lists every field, its type, default, allowed values and description. Editors use schemas to complete and check YAML files, and they document a configuration without reading the code.

`rompy schema` prints the schema of [`ModelRun`][rompy.model.ModelRun] by default, or of any class given by its full import path:

```bash
rompy schema -o modelrun.json
rompy schema rompy_xbeach.config.Config --format yaml -o xbeach.yaml
```

In Python, every class has `model_json_schema()`. In the `ModelRun` schema, the `config` field maps each `model_type` to a configuration class:

```python exec="on" source="above" result="text" session="configuration"
schema = ModelRun.model_json_schema()
print(schema["properties"]["config"]["discriminator"]["mapping"])
```

## Variables and includes in YAML files

When the `rompy` command line loads a YAML file, it also supports:

- **`${VAR}` substitution** from environment variables, with defaults (`${OUTPUT_ROOT:-./output}`) and date filters (`${CYCLE|as_datetime|shift:-1d}`), useful for scheduled runs. See [Templates](templates.md).
- **`!include`** to compose a file from others, for example a shared grid or backend configuration. Paths are relative to the including file.

Both are applied by the command line's loader. In Python, `yaml.safe_load` does neither; use [`load_yaml_with_includes`][rompy.core.yaml_loader.load_yaml_with_includes] and [`render_templates`][rompy.templating.render_templates] to do the same. See [the command line](../how-to/cli.md) and [YAML configurations](../how-to/yaml.md).

## What validation does not promise

Validation establishes that a configuration is complete and consistent with the declared rules. It cannot tell whether a dataset suits the question, whether boundary conditions represent reality, or whether the model has adequate skill. Those remain modelling decisions, to be checked by inspecting the generated inputs and validating the results.

## See it in the notebooks

- XBeach: [how components group the settings, and the checks they apply](https://rom-py.github.io/rompy-notebooks/notebooks/xbeach/tutorial/05_model_settings/), and [the same model as a YAML file and from the command line](https://rom-py.github.io/rompy-notebooks/notebooks/xbeach/tutorial/07_yaml_and_cli/).
- SWAN: [the checks rompy-swan applies](https://rom-py.github.io/rompy-notebooks/notebooks/swan/tutorial/05_model_settings/), and [the hindcast as a YAML file and from the command line](https://rom-py.github.io/rompy-notebooks/notebooks/swan/tutorial/07_yaml_and_cli/).
- The [rompy hands-on notebook](https://rom-py.github.io/rompy-notebooks/notebooks/common/rompy_hands_on/) writes a small plugin with its own checks.
