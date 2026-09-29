# Writing sources, backends and postprocessors

Besides models, rompy has five extension points: data sources, run backends, postprocessors, pipelines and file transfers. Each is a small class, registered under an entry-point group (see [Plugin architecture](architecture.md)). The examples on this page run when the docs are built; none needs a model, Docker or network access.

```python exec="on" session="extending"
# Hidden setup: quiet logging, a temporary folder and a generated workspace.
import tempfile
from pathlib import Path

from rompy.core.time import TimeRange
from rompy.logging import config as logging_config
from rompy.model import ModelRun

logging_config.update(level="WARNING")
TMP = Path(tempfile.mkdtemp())
```

## Sources

A source opens a dataset. Data objects such as [`DataGrid`][rompy.core.data.DataGrid] hold a source, and ask it for the variables and the part of the grid and period they need.

Subclass [`SourceBase`][rompy.core.source.SourceBase], give it a `model_type` literal, and implement `_open()` to return an `xarray.Dataset`. The inherited `open(variables, filters)` then selects variables and applies the `Filter` the data object builds from the grid and period.

```python exec="on" source="above" result="text" session="extending"
from typing import Literal

import numpy as np
import pandas as pd
import xarray as xr
from pydantic import Field
from rompy.core.filters import Filter
from rompy.core.source import SourceBase


class SourceSineWave(SourceBase):
    """Synthetic hourly wave heights, for tests and demonstrations."""

    model_type: Literal["sine_wave"] = Field("sine_wave", description="Model type discriminator")
    start: str = Field(description="First time")
    periods: int = Field(24, ge=1, description="Number of hourly records")
    mean: float = Field(1.5, description="Mean significant wave height (m)")

    def _open(self) -> xr.Dataset:
        time = pd.date_range(self.start, periods=self.periods, freq="h")
        hs = self.mean + 0.5 * np.sin(np.arange(self.periods) * 2 * np.pi / 12)
        tp = np.full(self.periods, 10.0)
        return xr.Dataset({"hs": ("time", hs), "tp": ("time", tp)}, coords={"time": time})


source = SourceSineWave(start="2023-01-01")
crop = Filter(crop={"time": slice("2023-01-01T00", "2023-01-01T03")})
print(source.open(variables=["hs"], filters=crop))
```

Register the class under `rompy.source`:

```toml
[project.entry-points."rompy.source"]
sine_wave = "mypackage.source:SourceSineWave"
```

The data objects accept only registered sources, because their `source` field is a union built from the entry points when rompy is imported. Until the package is installed, the source works on its own, as above, but a data object rejects it:

```python exec="on" source="above" result="text" session="extending"
from rompy.core.data import DataPoint

try:
    DataPoint(id="waves", source=source)
except Exception as err:
    print(err)
```

[`DataPoint`][rompy.core.data.DataPoint] accepts only the sources whose entry-point name ends in `:timeseries`, such as rompy's `"csv:timeseries"`; [`DataGrid`][rompy.core.data.DataGrid] accepts all of them. A model plugin can define its own source group instead, as rompy-xbeach does with `xbeach.source` for sources that carry a coordinate reference system.

## Run backends

A run backend runs a generated workspace. It has two parts:

- a **configuration class**, a subclass of [`BaseBackendConfig`][rompy.backends.config.BaseBackendConfig] with the backend's settings and a `get_backend_class()` method that returns the class that runs it;
- a **backend class** with `run(model_run, config, workspace_dir=None)`, which returns `True` on success.

[`ModelRun.run`][rompy.model.ModelRun.run] checks that it received a `BaseBackendConfig`, calls `get_backend_class()`, creates the backend and calls its `run`. rompy's [`LocalConfig`][rompy.backends.config.LocalConfig], [`DockerConfig`][rompy.backends.config.DockerConfig] and [`SlurmConfig`][rompy.backends.config.SlurmConfig] work this way.

This backend lists the workspace instead of running a model:

```python exec="on" source="above" result="text" session="extending"
from rompy.backends.config import BaseBackendConfig


class ListFilesConfig(BaseBackendConfig):
    """List the files of the workspace."""

    pattern: str = Field("*", description="Glob pattern of the files to list")

    def get_backend_class(self):
        return ListFilesRunBackend


class ListFilesRunBackend:
    """Backend that lists the workspace instead of running a model."""

    def run(self, model_run, config: ListFilesConfig, workspace_dir=None) -> bool:
        workspace = Path(workspace_dir or model_run.generate())
        for path in sorted(workspace.glob(config.pattern)):
            print(f"  {path.name}")
        return True


run = ModelRun(
    run_id="demo",
    period=TimeRange(start="2023-01-01", end="2023-01-02", interval="1h"),
    output_dir=TMP,
)
workspace = run.generate()
print(run.run(ListFilesConfig(), workspace_dir=workspace))
```

`BaseBackendConfig` provides `timeout`, `env_vars` and `working_dir`, and forbids unknown fields. A backend should honour them where they apply, and generate the workspace itself when `workspace_dir` is `None`.

Register the backend class under `rompy.run`:

```toml
[project.entry-points."rompy.run"]
listfiles = "mypackage.backends:ListFilesRunBackend"
```

!!! note "Custom backends from the command line"
    `rompy run CONFIG --backend-config FILE` and `rompy pipeline` read the backend type from the `type` key of the file and support `local`, `docker` and `slurm` only; the list is fixed in `rompy.cli`. A custom backend is used from Python by passing its configuration to [`ModelRun.run`][rompy.model.ModelRun.run]. The `rompy.run` entry point makes it appear in `rompy backends list`, which names it after the class without the `RunBackend` suffix (`ListFilesRunBackend` becomes `listfiles`).

## Postprocessors

A postprocessor also has two parts:

- a **configuration class**, a subclass of [`BasePostprocessorConfig`][rompy.postprocess.config.BasePostprocessorConfig] with a `type` literal, its settings, and `get_postprocessor_class()`;
- a **processor class** with `process(model_run, **settings)`, which returns a dictionary, by convention with a `success` key.

[`ModelRun.postprocess`][rompy.model.ModelRun.postprocess] calls `process` with the configuration's own fields as keyword arguments (it leaves out `timeout`, `env_vars`, `working_dir` and `type`), plus any keyword arguments given to `postprocess`. `process` should accept `**kwargs`: `rompy postprocess` also passes `output_dir` and `validate_outputs`.

```python exec="on" source="above" result="text" session="extending"
from rompy.postprocess.config import BasePostprocessorConfig


class CountFilesConfig(BasePostprocessorConfig):
    """Count the files in the workspace."""

    type: Literal["count_files"] = "count_files"
    pattern: str = Field("*", description="Glob pattern of the files to count")

    def get_postprocessor_class(self):
        return CountFilesPostprocessor


class CountFilesPostprocessor:
    """Postprocessor that counts files."""

    def process(self, model_run, pattern: str = "*", **kwargs) -> dict:
        workspace = Path(model_run.output_dir) / model_run.run_id
        files = [path for path in workspace.rglob(pattern) if path.is_file()]
        return {"success": True, "pattern": pattern, "count": len(files)}


print(run.postprocess(CountFilesConfig(pattern="*.md")))
```

Register both classes. The name under `rompy.postprocess.config` is the `type` a processor file uses, and should equal the `type` literal:

```toml
[project.entry-points."rompy.postprocess.config"]
count_files = "mypackage.postprocess:CountFilesConfig"

[project.entry-points."rompy.postprocess"]
count_files = "mypackage.postprocess:CountFilesPostprocessor"
```

With the package installed, `rompy postprocess model.yml --processor-config count.yml` loads this file into a `CountFilesConfig`:

```yaml
type: count_files
pattern: "*.nc"
```

## Pipeline backends

A pipeline backend runs the stages in order. [`ModelRun.pipeline`][rompy.model.ModelRun.pipeline] looks the backend up by name among the classes registered under `rompy.pipeline` and calls its `execute(model_run, **kwargs)`. The built-in [`LocalPipelineBackend`][rompy.pipeline.LocalPipelineBackend] (`"local"`) generates the workspace, runs it with `backend_config` and postprocesses it with `processor`, and works with custom backends and postprocessors:

```python exec="on" source="above" result="text" session="extending"
result = run.pipeline(
    pipeline_backend="local",
    backend_config=ListFilesConfig(pattern="*"),
    processor=CountFilesConfig(),
)
print(result["stages_completed"], result["postprocess_results"])
```

A new pipeline backend, for example one that submits the stages to a workflow service, is a class with `execute`:

```python
class CloudPipelineBackend:
    """Submit generate, run and postprocess to a workflow service."""

    def execute(self, model_run, backend_config=None, processor=None, **kwargs) -> dict:
        staging_dir = model_run.generate()
        job_id = submit(staging_dir, backend_config)  # your service's client
        return {"success": True, "run_id": model_run.run_id, "job_id": job_id}
```

```toml
[project.entry-points."rompy.pipeline"]
cloud = "mypackage.pipeline:CloudPipelineBackend"
```

The name `ModelRun.pipeline` accepts comes from the class name, not the entry-point name: the class name, lower-cased, without the `PipelineBackend` suffix. `CloudPipelineBackend` is therefore `"cloud"`; keep the class and entry-point names consistent.

## Transfers

A transfer copies files between a URI scheme and the local disk. [`DataBlob`][rompy.core.data.DataBlob] uses one to fetch its `source`, and [`TransferManager`][rompy.transfer.manager.TransferManager] to copy files to one or more destinations. [`get_transfer`][rompy.transfer.registry.get_transfer] picks the class from the scheme of the URI (a plain path is `file`).

Subclass [`TransferBase`][rompy.transfer.base.TransferBase] and implement its six methods: `get`, `exists`, `list`, `put`, `delete` and `stat`. A scheme that cannot support an operation raises [`UnsupportedOperation`][rompy.transfer.exceptions.UnsupportedOperation].

```python exec="on" source="above" result="text" session="extending"
from rompy.transfer import TransferBase


class MemoryTransfer(TransferBase):
    """Files held in a dictionary, under memory:// URIs."""

    store = {"memory://bathy/depth.txt": b"10.0\n"}

    def get(self, uri, destdir, name=None, link=False):
        destination = Path(destdir) / (name or uri.rsplit("/", 1)[-1])
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(self.store[uri])
        return destination

    def exists(self, uri):
        return uri in self.store

    def list(self, uri):
        return [key for key in self.store if key.startswith(uri)]

    def put(self, local_path, uri):
        self.store[uri] = Path(local_path).read_bytes()
        return uri

    def delete(self, uri, recursive=False):
        self.store.pop(uri, None)

    def stat(self, uri):
        return {"size": len(self.store[uri])}


copied = MemoryTransfer().get("memory://bathy/depth.txt", TMP / "inputs")
print(copied.name, copied.read_text())
```

Register one entry per scheme under `rompy.transfer`; the entry-point name is the scheme, and two packages cannot register the same scheme:

```toml
[project.entry-points."rompy.transfer"]
memory = "mypackage.transfer:MemoryTransfer"
```

Until then, the registry does not know the scheme, and its error lists the schemes it does know:

```python exec="on" source="above" result="text" session="extending"
from rompy.transfer import get_transfer

try:
    get_transfer("memory://bathy/depth.txt")
except KeyError as err:
    print(err)
```
