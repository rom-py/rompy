# Templates and rendering

Two kinds of templating happen in rompy, at different times:

| Syntax | When | What it fills in |
|---|---|---|
| `{{runtime.run_id}}`, `{{config.friction}}` | During [`generate()`][rompy.model.ModelRun.generate] | The model's input files, from the run and its configuration (Jinja2, through cookiecutter) |
| `${CYCLE}`, `${OUTPUT_ROOT:-./output}` | When a YAML file is loaded, before validation | Values in the YAML configuration, from environment variables |

```python exec="on" session="templates"
# Hidden setup: quiet logging and a temporary output folder.
import tempfile
from pathlib import Path

from rompy.logging import config as logging_config

logging_config.update(level="WARNING")
OUT_DIR = Path(tempfile.mkdtemp())
```

## The generation contract

[`ModelRun.generate()`][rompy.model.ModelRun.generate] asks the configuration for its content and then asks it to write the files:

```python
context = {
    "runtime": run.model_dump() | {"staging_dir": ..., "_generated_at": ..., ...},
    "config": config(run) if callable(config) else config,
}
config.render(context, run.output_dir)
```

- **`config(run)`** is where a model plugin does its work: it reads data sources, writes grid and forcing files into the workspace (`run.staging_dir`) and returns what the templates need. It can return the configuration itself or a dictionary. [`BaseConfig`][rompy.core.config.BaseConfig] returns itself.
- **`config.render(context, output_dir)`** writes the model's input files. [`BaseConfig.render`][rompy.core.config.BaseConfig.render] renders a cookiecutter template; a plugin can override it.

`context["runtime"]` also holds `staging_dir` (the workspace path), `_generated_at`, `_generated_by`, `_generated_on` and `_datefmt` (`%Y%m%d.%H%M%S`).

## The default: a cookiecutter template

[`BaseConfig`][rompy.core.config.BaseConfig] has two fields for rendering:

| Field | Meaning |
|---|---|
| `template` | Path or git URL of the template. The default is rompy's example template, `rompy/templates/base`. |
| `checkout` | Branch, tag or commit to use when the template is a git repository (default `main`) |

[`render`][rompy.core.render.render] uses cookiecutter, with two differences from plain cookiecutter:

- **No `cookiecutter.json` is needed.** The variables are `runtime` and `config` from the context.
- **The template's top folder is named after the workspace.** The template directory must contain one folder whose name uses a `runtime` variable, conventionally `{{runtime.staging_dir}}`. It renders to the workspace path, so everything inside it ends up in the workspace.

A template for a model with one input file:

```text
mytemplate/
└── {{runtime.staging_dir}}/
    └── model.inp
```

```python exec="on" source="above" result="text" session="templates"
template_dir = OUT_DIR / "mytemplate"
(template_dir / "{{runtime.staging_dir}}").mkdir(parents=True)
(template_dir / "{{runtime.staging_dir}}" / "model.inp").write_text(
    "RUN {{runtime.run_id}}\n"
    "START {{runtime.period.start.strftime('%Y%m%d.%H%M')}}\n"
    "FRICTION {{config.friction}}\n"
)
print((template_dir / "{{runtime.staging_dir}}" / "model.inp").read_text())
```

A configuration adds its own fields. In a model plugin the class also sets its own `model_type` and is registered under the `rompy.config` entry point; this one keeps `model_type: base` so that it can be used here without installing anything:

```python exec="on" source="above" result="text" session="templates"
from rompy.core.config import BaseConfig
from rompy.core.time import TimeRange
from rompy.model import ModelRun


class MyConfig(BaseConfig):
    friction: float = 0.02


run = ModelRun(
    run_id="templated",
    period=TimeRange(start="2023-01-01", end="2023-01-02", interval="1h"),
    output_dir=OUT_DIR / "runs",
    config=MyConfig(template=str(template_dir), friction=0.03),
)
workspace = run.generate()
print((workspace / "model.inp").read_text())
```

`runtime.period.start` is a `datetime` here, so Jinja2 can call its methods. Fields of the configuration are available as `config.<field>` because `BaseConfig.__call__` returns the configuration itself.

## Overriding render()

Some models are easier to write in code than in a template. A plugin then overrides [`render`][rompy.core.config.BaseConfig.render] and writes the files itself, and `template` and `checkout` are not used. The same example also returns a dictionary from `__call__`, which becomes `context["config"]`:

```python exec="on" source="above" result="text" session="templates"
class WaveConfig(BaseConfig):
    hs: float = 1.0

    def __call__(self, runtime):
        return {"hs": self.hs, "nsteps": len(runtime.period.date_range)}

    def render(self, context, output_dir):
        workspace = Path(context["runtime"]["staging_dir"])
        values = context["config"]
        (workspace / "waves.txt").write_text(
            f"HS {values['hs']}\nNSTEPS {values['nsteps']}\n"
        )


run = ModelRun(
    run_id="direct",
    period=TimeRange(start="2023-01-01", end="2023-01-02", interval="6h"),
    output_dir=OUT_DIR / "runs",
    config=WaveConfig(hs=2.5),
)
workspace = run.generate()
print(sorted(p.name for p in workspace.iterdir()))
print((workspace / "waves.txt").read_text())
```

Write into `context["runtime"]["staging_dir"]`: the `output_dir` argument is the run's output directory, not the workspace.

## `${VAR}` substitution in YAML

YAML configurations can take values from environment variables. The `rompy` command line substitutes them in every configuration file it reads (model, backend, postprocessor and pipeline files) after parsing the YAML and before validating it. In Python, call [`render_templates`][rompy.templating.render_templates] yourself; it uses `os.environ` unless given a `context`.

| Form | Result |
|---|---|
| `${VAR}` | The value of `VAR`; an error if it is not set |
| `${VAR:-default}` | The value of `VAR`, or `default` if it is not set |
| `${VAR|filter|filter:arg}` | The value passed through filters, left to right |

The filters work on dates:

| Filter | Does | Example |
|---|---|---|
| `as_datetime` | Parse ISO 8601 text to a datetime; `as_datetime:%Y%m%d%H` parses another format | `${CYCLE|as_datetime}` |
| `strftime:FORMAT` | Format a datetime (text is parsed as ISO 8601 first) | `${CYCLE|strftime:%Y%m%d}` |
| `shift:DELTA` | Add a time delta: `[+|-]<number><d|h|m|s>`, e.g. `+1d`, `-6h`, `+30m` | `${CYCLE|as_datetime|shift:-1d}` |

```python exec="on" source="above" result="text" session="templates"
from rompy.templating import render_templates

config = {
    "run_id": "cycle_${CYCLE|strftime:%Y%m%d}",
    "output_dir": "${OUTPUT_ROOT:-./output}/${CYCLE|strftime:%Y/%m/%d}",
    "period": {
        "start": "${CYCLE}",
        "end": "${CYCLE|as_datetime|shift:+1d}",
        "interval": "1h",
    },
    "wind_file": "wind_${CYCLE|as_datetime|shift:-6h|strftime:%Y%m%d%H}.nc",
    "timeout": "${JOB_TIMEOUT:-3600}",
}
rendered = render_templates(config, context={"CYCLE": "2023-01-01T00:00:00"})
for key, value in rendered.items():
    print(f"{key}: {value!r}")
```

### Types

A value that is exactly one expression keeps a type:

- With filters, the filter's result is kept as is: a datetime from `as_datetime` or `shift`, text from `strftime`.
- Without filters, text is converted: `true`, `yes`, `1` become `True`; `false`, `no`, `0` become `False`; other whole numbers become `int` and decimals `float`.

An expression inside longer text is always converted to text.

Because `1` and `0` become booleans, and numbers become numbers, a value that is exactly `${VAR}` cannot fill a field that only accepts text, such as a backend's `env_vars`. A backend config with `OMP_NUM_THREADS: "${NTHREADS}"` fails validation when `NTHREADS=4`.

### Errors

Unset variables without a default, unknown filters and bad deltas raise a [`TemplateError`][rompy.templating.TemplateError]:

```python exec="on" source="above" result="text" session="templates"
from rompy.templating import TemplateError

for value in ["${MISSING}", "${CYCLE|upper}", "${CYCLE|shift:1w}"]:
    try:
        render_templates({"value": value}, context={"CYCLE": "2023-01-01"})
    except TemplateError as err:
        print(err)
```

With `strict=False`, unresolved expressions are left as they are.

## See also

- [Writing and sharing YAML configurations](../how-to/yaml.md): `!include`, `${VAR}` and loading YAML in Python.
- [The run lifecycle](run-lifecycle.md): where rendering fits.
- Reference: [templates and rendering](../reference/templates.md), [model configuration](../reference/config.md).
