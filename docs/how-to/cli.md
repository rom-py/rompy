# The command line

The `rompy` command validates, generates, runs and postprocesses models described in YAML or JSON files. It does what the Python API does, with the configuration in files instead of code.

| Command | Does | Python equivalent |
|---|---|---|
| `rompy validate CONFIG` | Checks a run configuration | `ModelRun(**data)` |
| `rompy generate CONFIG` | Writes the workspace | [`ModelRun.generate`][rompy.model.ModelRun.generate] |
| `rompy run CONFIG --backend-config FILE` | Generates and runs the model | [`ModelRun.run`][rompy.model.ModelRun.run] |
| `rompy postprocess CONFIG --processor-config FILE` | Postprocesses the outputs | [`ModelRun.postprocess`][rompy.model.ModelRun.postprocess] |
| `rompy pipeline FILE` | Generates, runs and postprocesses | [`ModelRun.pipeline`][rompy.model.ModelRun.pipeline] |
| `rompy schema [MODEL_TYPE]` | Prints a JSON schema | `ModelRun.model_json_schema()` |
| `rompy backends list|validate|schema|create` | Lists and checks backend configurations | |

The examples on this page run the commands through click's test runner so that their output is shown here. In a shell, type the same arguments after `rompy`.

```python exec="on" source="above" session="cli"
from click.testing import CliRunner

from rompy.cli import cli


def rompy(*args):
    result = CliRunner().invoke(cli, list(args), prog_name="rompy")
    print(result.output.rstrip())
```

```python exec="on" session="cli"
# Hidden setup: a temporary folder with a run configuration.
import tempfile
from pathlib import Path

OUT_DIR = Path(tempfile.mkdtemp())
CONFIG = OUT_DIR / "run.yml"
CONFIG.write_text(f"""\
run_id: cli_demo
output_dir: {OUT_DIR}/runs
period:
  start: "2023-01-01T00:00"
  end: "2023-01-02T00:00"
  interval: 1h
config:
  model_type: base
""")
```

```python exec="on" source="above" result="text" session="cli"
rompy("--help")
```

`rompy --version` prints the version and the model types installed:

```python exec="on" source="above" result="text" session="cli"
rompy("--version")
```

## Configuration files

`CONFIG` is a YAML or JSON file describing a [`ModelRun`][rompy.model.ModelRun]:

```yaml
run_id: cli_demo
output_dir: ./runs
period:
  start: "2023-01-01T00:00"
  end: "2023-01-02T00:00"
  interval: 1h
config:
  model_type: base    # or xbeach, swan, schism, ... with that model's settings
```

Every file the command line reads (run, backend, postprocessor and pipeline files) is processed the same way:

1. YAML is parsed with `!include` support; if that fails, the file is read as JSON.
2. `${VAR}` expressions are replaced from the environment. An unset variable without a default is an error.
3. The result is validated.

See [Writing and sharing YAML configurations](yaml.md) for `!include` and `${VAR}`.

### Configuration from an environment variable

With `--config-from-env`, the run configuration is read from the `ROMPY_CONFIG` environment variable instead of a file, as JSON or YAML. `!include` paths are then relative to the current directory. This suits containers and CI jobs:

```bash
export ROMPY_CONFIG="$(cat run.yml)"
rompy generate --config-from-env
```

Give either a file or `--config-from-env`, not both.

## Options for every command

| Option | Environment variable | Meaning |
|---|---|---|
| `-v`, `-vv` | | Log at INFO, or DEBUG. Without `-v` only warnings and errors are shown. |
| `--log-dir DIR` | `ROMPY_LOG_DIR` | Also write the log to `DIR/rompy.log` |
| `--simple-logs` / `--detailed-logs` | `ROMPY_SIMPLE_LOGS` | Messages only, or with time, level and module (default) |
| `--ascii-only` / `--unicode` | `ROMPY_ASCII_ONLY` | Draw boxes and symbols with ASCII characters |
| `--show-warnings` / `--hide-warnings` | | Show Python deprecation warnings |
| `--config-from-env` | `ROMPY_CONFIG` | Read the run configuration from the environment |

See [Logging and output formatting](logging.md).

## validate

Checks a run configuration without writing anything:

```python exec="on" source="above" result="text" session="cli"
rompy("validate", str(CONFIG), "-v", "--simple-logs")
```

An invalid file fails with the validation error and a non-zero exit code.

## generate

Writes the workspace, `output_dir/run_id`. `--output-dir` replaces the `output_dir` of the file:

```python exec="on" source="above" result="text" session="cli"
rompy("generate", str(CONFIG), "--output-dir", str(OUT_DIR / "test_inputs"))
print(sorted(p.name for p in (OUT_DIR / "test_inputs" / "cli_demo").iterdir()))
```

## run

Generates the workspace and runs the model with a [backend configuration](../concepts/backends.md). The backend file has a `type` key, `local`, `docker` or `slurm`:

```yaml
# docker.yml
type: docker
image: xbeach:latest
executable: xbeach
mpiexec: mpirun
cpu: 4
```

```bash
rompy run run.yml --backend-config docker.yml
rompy run run.yml --backend-config docker.yml --dry-run         # generate only
rompy generate run.yml                                          # or generate first,
rompy run run.yml --backend-config docker.yml --skip-generate   # then run the existing workspace
```

| Option | Meaning |
|---|---|
| `--backend-config FILE` | Backend configuration (required) |
| `--dry-run` | Generate the workspace but do not run |
| `--skip-generate` | Run the existing workspace; it must exist and not be empty |

With a local backend and a shell command in place of a model, the whole run works here:

```python exec="on" source="above" result="text" session="cli"
backend = OUT_DIR / "local.yml"
backend.write_text("type: local\ncommand: echo finished > run.log\n")

rompy("run", str(CONFIG), "--backend-config", str(backend))
print((OUT_DIR / "runs" / "cli_demo" / "run.log").read_text())
```

## postprocess

Runs a postprocessor on the outputs of a run. The postprocessor file's `type` selects a postprocessor registered under the `rompy.postprocess.config` entry point; rompy ships `noop`.

```bash
rompy postprocess run.yml --processor-config noop.yml
```

| Option | Meaning |
|---|---|
| `--processor-config FILE` | Postprocessor configuration (required) |
| `--output-dir DIR` | Folder to postprocess instead of the workspace |
| `--validate-outputs` / `--no-validate` | Passed to the postprocessor (default: validate) |

## pipeline

Generates, runs and postprocesses from one file with three sections, `config`, `backend` and `postprocessor`, each inline or included from another file:

```yaml
# pipeline.yml
config: !include run.yml
backend: !include backends/local.yml
postprocessor:
  type: noop
```

```bash
rompy pipeline pipeline.yml
rompy pipeline pipeline.yml --backend-config backends/docker.yml
```

| Option | Meaning |
|---|---|
| `--backend-config FILE` | Use this backend instead of the `backend` section |
| `--processor-config FILE` | Use this postprocessor instead of the `postprocessor` section |
| `--cleanup-on-failure` / `--no-cleanup` | Delete the workspace if the run fails (default: keep) |
| `--validate-stages` / `--no-validate` | Check the workspace exists after generating (default: check) |

See [Pipelines](../concepts/backends.md#pipelines).

## schema

Prints the JSON schema of a model class, by default [`ModelRun`][rompy.model.ModelRun] with every installed model configuration. Editors use it to complete and check YAML files; see [Writing and sharing YAML configurations](yaml.md#a-json-schema-for-your-editor).

```bash
rompy schema -o modelrun.schema.json
rompy schema --format yaml -o modelrun.schema.yaml
rompy schema rompy_xbeach.config.Config -o xbeach.schema.json
```

`MODEL_TYPE` is a class name from `rompy.model` or a full import path such as `rompy_xbeach.config.Config`. A model type name such as `xbeach` is not recognised.

```python exec="on" source="above" result="text" session="cli"
import json

rompy("schema", "-o", str(OUT_DIR / "modelrun.schema.json"))
schema = json.loads((OUT_DIR / "modelrun.schema.json").read_text())
print(list(schema["properties"]))
```

## backends

Four subcommands help with backend configuration files:

| Command | Does |
|---|---|
| `rompy backends list` | Lists the installed run backends, postprocessors and pipeline backends (use `-v`) |
| `rompy backends create --backend-type local|docker [--with-examples] [--output FILE] [--format yaml|json]` | Prints or writes a starting file |
| `rompy backends validate FILE [--backend-type local|docker]` | Validates a local or Docker backend file; the type comes from `--backend-type` or the file's `type` |
| `rompy backends validate FILE --processor-type noop` | Validates a postprocessor file |
| `rompy backends schema --backend-type local|docker [--format json|yaml]` | Prints the JSON schema of a backend configuration |

`create`, `validate` and `schema` cover the local and Docker backends; `rompy run` also accepts `type: slurm`.

```python exec="on" source="above" result="text" session="cli"
rompy("backends", "list", "-v", "--simple-logs")
```

```python exec="on" source="above" result="text" session="cli"
rompy("backends", "create", "--backend-type", "local", "--output", str(OUT_DIR / "new.yml"))
print((OUT_DIR / "new.yml").read_text())
rompy("backends", "validate", str(OUT_DIR / "new.yml"), "-v", "--simple-logs")
```

```python exec="on" session="cli"
# Hidden: restore the logging configuration the commands changed.
from rompy.logging import config as logging_config

logging_config.update(level="WARNING", format="verbose", use_ascii=False)
logging_config.configure_logging()
```

## See also

- [The run lifecycle](../concepts/run-lifecycle.md) and [Backends, postprocessors and pipelines](../concepts/backends.md).
- Notebooks: YAML and the command line for [XBeach](https://rom-py.github.io/rompy-notebooks/notebooks/xbeach/tutorial/07_yaml_and_cli/) and [SWAN](https://rom-py.github.io/rompy-notebooks/notebooks/swan/tutorial/07_yaml_and_cli/).
