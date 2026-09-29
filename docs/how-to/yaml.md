# Writing and sharing YAML configurations

Every rompy object can be written as YAML: the keys are the field names and nested objects are nested mappings. A YAML file describes a run completely, so it can be kept under version control, reviewed, shared and run with the [command line](cli.md) or loaded in Python.

```python exec="on" session="yaml"
# Hidden setup: quiet logging and a temporary folder.
import tempfile
from pathlib import Path

from rompy.logging import config as logging_config

logging_config.update(level="WARNING")
OUT_DIR = Path(tempfile.mkdtemp())
```

## A run in YAML

A run file describes a [`ModelRun`][rompy.model.ModelRun]:

```yaml
run_id: beach_2023
output_dir: ./runs
period:
  start: "2023-01-01T00:00"
  end: "2023-01-02T00:00"
  interval: 1h
config:
  model_type: base
```

Load it by parsing the YAML and passing the result to `ModelRun`:

```python exec="on" source="above" result="text" session="yaml"
import yaml

from rompy.model import ModelRun

text = """
run_id: beach_2023
output_dir: ./runs
period:
  start: "2023-01-01T00:00"
  end: "2023-01-02T00:00"
  interval: 1h
config:
  model_type: base
"""
run = ModelRun(**yaml.safe_load(text))
print(run.run_id, run.period.start, type(run.config).__name__)
```

### model_type selects the class

Where a field can hold one of several classes, a `model_type` key says which. For `config` the choices are the model configurations registered by the installed plugins under the `rompy.config` entry point: `base` from rompy, `xbeach` from rompy-xbeach, and so on. Plugins use the same key for their own choices, such as a wave model or a friction formulation; see the [rompy-xbeach parameter reference](https://rom-py.github.io/rompy-xbeach/reference/parameters/) for an example.

An unknown `model_type` lists the installed choices:

```python exec="on" source="above" result="text" session="yaml"
from pydantic import ValidationError

try:
    ModelRun(config={"model_type": "wavewatch"})
except ValidationError as err:
    print(err.errors()[0]["msg"])
```

### Misspelled keys are errors

rompy objects reject keys they do not know, and suggest the closest field name:

```python exec="on" source="above" result="text" session="yaml"
try:
    ModelRun(run_id="beach_2023", outputdir="./runs")
except ValidationError as err:
    print(err.errors()[0]["msg"])
```

## Writing YAML from Python

A run built in Python can be written out and loaded again:

```python exec="on" source="above" result="text" session="yaml"
from rompy.core.time import TimeRange

run = ModelRun(
    run_id="beach_2023",
    period=TimeRange(start="2023-01-01", end="2023-01-02", interval="1h"),
    output_dir="./runs",
)
text = yaml.safe_dump(run.model_dump(mode="json"), sort_keys=False)
print(text)
print(ModelRun(**yaml.safe_load(text)) == run)
```

The dump includes every field with its value, including defaults such as the absolute path of the template. Remove what should not be fixed before sharing the file.

## Splitting files with `!include`

`!include path` replaces a value with the contents of another YAML file. Shared pieces, such as a model setup used by several runs or a backend used by several pipelines, can then live in one file. Use [`load_yaml_with_includes`][rompy.core.yaml_loader.load_yaml_with_includes] to read such files in Python; the command line does this for every file.

```python exec="on" source="above" result="text" session="yaml"
from rompy.core.yaml_loader import load_yaml_with_includes

(OUT_DIR / "shared").mkdir()
(OUT_DIR / "shared" / "january.yml").write_text(
    'start: "2023-01-01"\nend: "2023-02-01"\ninterval: 1h\n'
)
(OUT_DIR / "run.yml").write_text("""
run_id: january
output_dir: ./runs
period: !include shared/january.yml
config:
  model_type: base
""")

data = load_yaml_with_includes(OUT_DIR / "run.yml")
print(data["period"])
print(ModelRun(**data).period.end)
```

- A relative path is relative to the file that contains the `!include`; an absolute path is used as is.
- Environment variables in the path are expanded, e.g. `!include $CONFIG_DIR/period.yml`.
- An included file can include others, up to 10 levels. A file that includes itself, directly or through others, is an error.
- The included content replaces the value; it is not merged with keys next to it.

## Environment variables with `${VAR}`

Values that change between machines or cycles, such as data paths or the forecast cycle, can come from environment variables:

```yaml
run_id: "cycle_${CYCLE|strftime:%Y%m%d}"
output_dir: "${OUTPUT_ROOT:-./runs}"
period:
  start: "${CYCLE}"
  end: "${CYCLE|as_datetime|shift:+1d}"
  interval: 1h
config:
  model_type: base
```

The command line replaces them after reading the YAML (and its includes) and before validating. In Python, call [`render_templates`][rompy.templating.render_templates] between the two steps:

```python exec="on" source="above" result="text" session="yaml"
from rompy.templating import render_templates

(OUT_DIR / "cycle.yml").write_text("""
run_id: "cycle_${CYCLE|strftime:%Y%m%d}"
output_dir: "${OUTPUT_ROOT:-./runs}"
period:
  start: "${CYCLE}"
  end: "${CYCLE|as_datetime|shift:+1d}"
  interval: 1h
config:
  model_type: base
""")

# The values come from os.environ unless a context is given
data = render_templates(
    load_yaml_with_includes(OUT_DIR / "cycle.yml"),
    context={"CYCLE": "2023-01-01T00:00:00"},
)
run = ModelRun(**data)
print(run.run_id, run.output_dir, run.period.end)
```

[Templates and rendering](../concepts/templates.md#var-substitution-in-yaml) lists the syntax, the date filters and how values are typed.

## A JSON schema for your editor

A JSON schema describes every field, its type and its allowed values. Editors with a YAML language server, such as VS Code with the YAML extension, use it to complete keys and flag errors while you type. Write the schema of `ModelRun`, which includes every installed model configuration:

```bash
rompy schema -o modelrun.schema.json
```

and point the YAML file at it on its first line:

```yaml
# yaml-language-server: $schema=./modelrun.schema.json
run_id: beach_2023
```

The same schema is available in Python. The `config` field shows how `model_type` selects the class:

```python exec="on" source="above" result="text" session="yaml"
schema = ModelRun.model_json_schema()
print(list(schema["properties"]))
print(schema["properties"]["config"]["discriminator"])
```

## Sharing configurations

- Keep the run file free of machine-specific settings: put the backend in its own file (see [Backends](../concepts/backends.md#backend-configurations-in-yaml)) and paths in `${VAR}` expressions.
- Put settings shared by several runs in files pulled in with `!include`.
- Check a file before running it: `rompy validate run.yml`.

## See also

- [The command line](cli.md).
- Notebooks: YAML and the command line for [XBeach](https://rom-py.github.io/rompy-notebooks/notebooks/xbeach/tutorial/07_yaml_and_cli/) and [SWAN](https://rom-py.github.io/rompy-notebooks/notebooks/swan/tutorial/07_yaml_and_cli/).
- Reference: [YAML loading](../reference/yaml.md), [templates and rendering](../reference/templates.md).
