# Backend internals

This page is for developers adding a way to run models, to postprocess their outputs or to chain the steps. [Backends, postprocessors and pipelines](../concepts/backends.md) describes how to use the built-in ones.

```python exec="on" session="internals"
# Hidden setup: quiet logging and a temporary output folder.
import tempfile
from pathlib import Path

from rompy.logging import config as logging_config

logging_config.update(level="WARNING")
OUT_DIR = Path(tempfile.mkdtemp())
```

Each extension is a pair: a Pydantic configuration class that users create and validate, and a plain class that does the work.

| Extension | Configuration class | Worker class | Called by |
|---|---|---|---|
| Run backend | subclass of [`BaseBackendConfig`][rompy.backends.config.BaseBackendConfig] | `run(model_run, config, workspace_dir=None) -> bool` | [`ModelRun.run`][rompy.model.ModelRun.run] |
| Postprocessor | subclass of [`BasePostprocessorConfig`][rompy.postprocess.config.BasePostprocessorConfig] | `process(model_run, **fields) -> dict` | [`ModelRun.postprocess`][rompy.model.ModelRun.postprocess] |
| Pipeline backend | none, keyword arguments | `execute(model_run, **kwargs) -> dict` | [`ModelRun.pipeline`][rompy.model.ModelRun.pipeline] |

## Run backends

### How a run finds its backend

[`ModelRun.run(backend, workspace_dir=None)`][rompy.model.ModelRun.run]:

1. checks that `backend` is a `BaseBackendConfig` instance, and raises `TypeError` otherwise;
2. calls `backend.get_backend_class()` and creates the class with no arguments;
3. calls its `run(model_run, config=backend, workspace_dir=workspace_dir)` and returns the result.

The configuration decides the backend, so no registry is consulted. The built-in pairs are:

| Configuration | Backend |
|---|---|
| [`LocalConfig`][rompy.backends.config.LocalConfig] | [`LocalRunBackend`][rompy.run.LocalRunBackend] |
| [`DockerConfig`][rompy.backends.config.DockerConfig] | [`DockerRunBackend`][rompy.run.docker.DockerRunBackend] |
| [`SlurmConfig`][rompy.backends.config.SlurmConfig] | [`SlurmRunBackend`][rompy.run.slurm.SlurmRunBackend] |

### The contract

A backend's `run()` method:

- **Uses the workspace it is given.** If `workspace_dir` is `None`, it calls `model_run.generate()` first; the built-in backends do this so that `run()` works on an ungenerated run.
- **Returns `True` or `False`.** Return `False` when the model fails, and log why. The local backend raises `TimeoutError` when the timeout is exceeded.
- **Reads its settings from `config`.** The common ones are `timeout`, `env_vars` and `working_dir`; the default working directory is the workspace.

### Writing one

The configuration class adds the fields the backend needs and returns the backend class. Configuration classes forbid unknown fields, and validators check values when the object is created. This backend writes a file instead of running a model:

```python exec="on" source="above" result="text" session="internals"
from rompy.backends.config import BaseBackendConfig
from rompy.core.time import TimeRange
from rompy.model import ModelRun


class EchoConfig(BaseBackendConfig):
    """Write a message into the workspace."""

    message: str = "hello"

    def get_backend_class(self):
        return EchoRunBackend


class EchoRunBackend:
    def run(self, model_run, config, workspace_dir=None):
        workspace = Path(workspace_dir or model_run.generate())
        (workspace / "echo.txt").write_text(config.message)
        return True


run = ModelRun(
    run_id="echo",
    period=TimeRange(start="2023-01-01", end="2023-01-02", interval="1h"),
    output_dir=OUT_DIR,
)
print(run.run(EchoConfig(message="model finished", timeout=600)))
print((run.staging_dir / "echo.txt").read_text())
```

Register the backend class so that `rompy backends list` shows it:

```toml
[project.entry-points."rompy.run"]
echo = "mypackage.backends:EchoRunBackend"
```

The list is keyed by the class name, lower-cased, without `RunBackend` (`echo` here).

!!! note "Backend files on the command line"
    `rompy run --backend-config` maps the file's `type` key to a class with a fixed table in `rompy.cli` (`local`, `docker`, `slurm`). A new backend configuration is used from Python, or through a pipeline backend that builds it.

## Postprocessors

### How a postprocessor is called

[`ModelRun.postprocess(processor, **kwargs)`][rompy.model.ModelRun.postprocess]:

1. checks that `processor` is a `BasePostprocessorConfig` instance;
2. calls `processor.get_postprocessor_class()` and creates the class with no arguments;
3. dumps the configuration, drops `timeout`, `env_vars`, `working_dir` and `type`, updates the rest with `kwargs`;
4. calls `process(model_run, **fields)` and returns the dictionary it gives back.

So the configuration's own fields arrive as keyword arguments. By convention the result has a `success` key; the pipeline logs a warning when it is `False`.

### Writing one

The configuration has a `type` literal, used to pick the class when a YAML file is loaded:

```python exec="on" source="above" result="text" session="internals"
from typing import Literal

from rompy.postprocess.config import BasePostprocessorConfig


class ListFilesConfig(BasePostprocessorConfig):
    """List the files in the workspace."""

    type: Literal["list_files"] = "list_files"
    pattern: str = "*"

    def get_postprocessor_class(self):
        return ListFilesPostprocessor


class ListFilesPostprocessor:
    def process(self, model_run, pattern="*", **kwargs):
        files = sorted(p.name for p in model_run.staging_dir.glob(pattern))
        return {"success": True, "run_id": model_run.run_id, "files": files}


print(run.postprocess(ListFilesConfig(pattern="*.txt")))
print(run.postprocess(ListFilesConfig(), pattern="*"))
```

Register both classes. The name in `rompy.postprocess.config` must equal `type`: the command line uses it to find the configuration class for a file with that `type`.

```toml
[project.entry-points."rompy.postprocess.config"]
list_files = "mypackage.postprocess:ListFilesConfig"

[project.entry-points."rompy.postprocess"]
list_files = "mypackage.postprocess:ListFilesPostprocessor"
```

`rompy.postprocess` feeds `rompy backends list`, keyed by class name without `Postprocessor`.

## Pipeline backends

[`ModelRun.pipeline(pipeline_backend="local", **kwargs)`][rompy.model.ModelRun.pipeline] looks up the pipeline backend by name, creates it with no arguments and returns `execute(model_run, **kwargs)`. The built-in [`LocalPipelineBackend`][rompy.pipeline.LocalPipelineBackend] takes `backend_config`, `processor`, `process_kwargs`, `cleanup_on_failure` and `validate_stages`, and calls `generate()`, `run()` and `postprocess()` in this process.

A pipeline backend that submits the steps elsewhere, for example to a workflow engine, implements `execute()` and returns a dictionary with at least `success`:

```python
class WorkflowPipelineBackend:
    def execute(self, model_run, backend_config=None, processor=None, **kwargs):
        workflow = build_workflow(model_run, backend_config, processor)
        job = workflow.submit()
        return {"success": job.wait(), "run_id": model_run.run_id}
```

```toml
[project.entry-points."rompy.pipeline"]
workflow = "mypackage.pipeline:WorkflowPipelineBackend"
```

The name `pipeline()` accepts is taken from the class name, lower-cased, without `PipelineBackend` (`workflow` here), not from the entry point name; keep the two the same. `rompy pipeline` always uses the `local` pipeline backend.

## Testing

- Test the configuration's validators both ways, and that `get_backend_class()` returns the right class.
- Test the worker with the external tool mocked: `subprocess.run` for command-line tools, `docker.from_env` for Docker, `sbatch` and `scontrol` for SLURM. `tests/backends/` has examples for the built-in backends.
- Run a real model only in integration tests that skip when the tool is missing, as `tests/integration/` does for Docker.

See [Testing](testing.md).

## See also

- Reference: [run backends](../reference/backends.md), [postprocessors](../reference/postprocess.md), [pipelines](../reference/pipeline.md).
