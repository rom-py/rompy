# Backends, postprocessors and pipelines

A model configuration says what to simulate. A backend configuration says where and how to run it: on this machine, in a Docker container or on a SLURM cluster. The same run can be given any of them, and neither the model configuration nor the generated workspace changes.

```python exec="on" session="backends"
# Hidden setup: quiet logging and a temporary output folder.
import tempfile
from pathlib import Path

from rompy.logging import config as logging_config

logging_config.update(level="WARNING")
OUT_DIR = Path(tempfile.mkdtemp())
```

| Object | Chooses | Used by |
|---|---|---|
| Backend configuration: [`LocalConfig`][rompy.backends.config.LocalConfig], [`DockerConfig`][rompy.backends.config.DockerConfig], [`SlurmConfig`][rompy.backends.config.SlurmConfig] | How the model runs | [`ModelRun.run`][rompy.model.ModelRun.run], `rompy run --backend-config` |
| Postprocessor configuration: [`NoopPostprocessorConfig`][rompy.postprocess.config.NoopPostprocessorConfig] | What happens to the outputs | [`ModelRun.postprocess`][rompy.model.ModelRun.postprocess], `rompy postprocess --processor-config` |
| Pipeline backend: `"local"` ([`LocalPipelineBackend`][rompy.pipeline.LocalPipelineBackend]) | How generate, run and postprocess are chained | [`ModelRun.pipeline`][rompy.model.ModelRun.pipeline], `rompy pipeline` |

Configurations are Pydantic models: they are validated when created, reject unknown fields and can be written as YAML. Each one names the class that does the work, so `run()` needs no other argument.

## Common settings

Every backend configuration inherits from [`BaseBackendConfig`][rompy.backends.config.BaseBackendConfig]:

| Field | Default | Meaning |
|---|---|---|
| `timeout` | 3600 | Maximum run time in seconds, 60 to 86400 |
| `env_vars` | `{}` | Environment variables for the run; keys and values must be text |
| `working_dir` | `None` | Folder to run in, which must exist; by default the workspace |

## Local

[`LocalConfig`][rompy.backends.config.LocalConfig] runs a shell command in the workspace:

```python exec="on" source="above" result="text" session="backends"
from rompy.backends import LocalConfig
from rompy.core.time import TimeRange
from rompy.model import ModelRun

run = ModelRun(
    run_id="local",
    period=TimeRange(start="2023-01-01", end="2023-01-02", interval="1h"),
    output_dir=OUT_DIR,
)
workspace = run.generate()

backend = LocalConfig(
    command="echo threads=$OMP_NUM_THREADS > run.log",
    env_vars={"OMP_NUM_THREADS": "4"},
    timeout=600,
)
print(run.run(backend, workspace_dir=workspace))
print((workspace / "run.log").read_text())
```

| Field | Meaning |
|---|---|
| `command` | Shell command to run. Without one, the backend calls `config.run(model_run)` if the model configuration has a `run` method, and otherwise does nothing. |
| `stream_output` | Log the command's output line by line while it runs, instead of at the end |

For a real model, `command` is the executable, e.g. `command="xbeach"` or `command="mpirun -n 4 swan.exe"`. A non-zero exit code makes `run()` return `False`; exceeding `timeout` raises `TimeoutError`.

`LocalConfig` also has `shell` and `capture_output` fields. They are validated, but the local backend always runs commands through the shell and captures their output.

## Docker

[`DockerConfig`][rompy.backends.config.DockerConfig] runs the model in a container. The workspace is mounted at `/app/run_id`, and the container runs

```bash
cd /app/run_id && <executable>
# or, with mpiexec set:
cd /app/run_id && <mpiexec> --allow-run-as-root -n <cpu> <executable>
```

```python
from rompy.backends import DockerConfig

backend = DockerConfig(
    image="xbeach:latest",
    executable="xbeach",
    mpiexec="mpirun",
    cpu=4,
    volumes=["/data/forcing:/data/forcing:ro"],
)
run.run(backend, workspace_dir=workspace)
```

| Field | Meaning |
|---|---|
| `image` | Image to use |
| `dockerfile`, `build_context`, `build_args` | Build an image instead. `dockerfile` is relative to `build_context`. The image is tagged from a hash of the Dockerfile and build arguments, and reused if it exists. |
| `executable` | Command run in the container (default `/usr/local/bin/run.sh`) |
| `cpu` | Number of MPI processes when `mpiexec` is set, 1 to 128 |
| `mpiexec` | MPI launcher, e.g. `mpirun`; empty for a serial run |
| `volumes` | Extra mounts, `host:container[:mode]`; the host path must exist |

Exactly one of `image` and `dockerfile` is required:

```python exec="on" source="above" result="text" session="backends"
from pydantic import ValidationError

from rompy.backends import DockerConfig

for kwargs in [{}, {"image": "swan:latest", "dockerfile": "Dockerfile"}]:
    try:
        DockerConfig(**kwargs)
    except ValidationError as err:
        print(err.errors()[0]["msg"])
```

`DockerConfig` also has `memory`, `user` and `remove_container` fields, and the common `timeout`. They are validated, but the Docker backend currently runs the container as root, removes it afterwards and does not apply a memory limit or timeout.

## SLURM

[`SlurmConfig`][rompy.backends.config.SlurmConfig] submits the run to a SLURM cluster and waits for it:

```python exec="on" source="above" result="text" session="backends"
from rompy.backends import SlurmConfig

backend = SlurmConfig(
    command="srun xbeach",
    queue="work",
    nodes=1,
    ntasks=16,
    time_limit="02:00:00",
    account="myproject",
    timeout=7200,
)
print(backend.model_dump(exclude_defaults=True))
```

The backend writes a job script with an `#SBATCH` line for each setting (`queue` becomes `--partition`), changes to the workspace, exports `env_vars` and runs `command`. It submits the script with `sbatch` and polls `scontrol show job` until the job ends; `run()` returns `True` if the job state is `COMPLETED`. The `timeout` is how long rompy waits, separate from SLURM's `time_limit`. Job output goes to `slurm-<jobid>.out` and `.err` in the workspace unless `output_file` and `error_file` are set. `additional_options` adds further `#SBATCH` lines, e.g. `["--gres=gpu:1"]`.

## Backend configurations in YAML

In a YAML file for the command line, a `type` key selects the class: `local`, `docker` or `slurm`. The other keys are the fields:

```yaml
type: docker
image: xbeach:latest
executable: xbeach
mpiexec: mpirun
cpu: 4
timeout: 7200
```

```bash
rompy run model.yml --backend-config docker.yml
```

`type` is read by the command line; it is not a field of the classes. To load such a file in Python, remove it and pick the class:

```python exec="on" source="above" result="text" session="backends"
import yaml

BACKENDS = {"local": LocalConfig, "docker": DockerConfig, "slurm": SlurmConfig}

data = yaml.safe_load("""
type: local
command: echo hello
timeout: 600
""")
backend = BACKENDS[data.pop("type")](**data)
print(repr(backend))
```

`rompy backends create --backend-type local` prints a starting file, and `rompy backends validate FILE` checks one (local and Docker files). See [The command line](../how-to/cli.md).

## Postprocessors

A postprocessor acts on the outputs after the run. Its configuration inherits `timeout`, `env_vars` and `working_dir` from [`BasePostprocessorConfig`][rompy.postprocess.config.BasePostprocessorConfig] and has a `type`. rompy ships one, `noop` ([`NoopPostprocessorConfig`][rompy.postprocess.config.NoopPostprocessorConfig]), which checks that the workspace exists when `validate_outputs` is true; plugins add others under the `rompy.postprocess.config` entry point.

```python exec="on" source="above" result="text" session="backends"
from rompy.postprocess.config import NoopPostprocessorConfig

results = run.postprocess(NoopPostprocessorConfig(validate_outputs=True))
print(results)
```

[`postprocess()`][rompy.model.ModelRun.postprocess] passes the configuration's own fields (all except `timeout`, `env_vars`, `working_dir` and `type`) to the postprocessor as keyword arguments, and returns the dictionary it produces. Extra keyword arguments to `postprocess()` override them.

In YAML the `type` key selects the configuration class from the registered ones:

```yaml
type: noop
validate_outputs: true
```

```bash
rompy postprocess model.yml --processor-config noop.yml
```

## Pipelines

[`pipeline()`][rompy.model.ModelRun.pipeline] generates, runs and postprocesses in one call. The built-in `"local"` pipeline backend calls [`generate()`][rompy.model.ModelRun.generate], [`run()`][rompy.model.ModelRun.run] and [`postprocess()`][rompy.model.ModelRun.postprocess] in turn, in this process; the run step itself can still use Docker or SLURM.

```python exec="on" source="above" result="text" session="backends"
results = run.pipeline(
    pipeline_backend="local",
    backend_config=LocalConfig(command="echo done > run.log"),
    processor=NoopPostprocessorConfig(),
)
for key in ["success", "stages_completed", "backend", "processor", "message"]:
    print(f"{key}: {results[key]}")
```

| Argument | Meaning |
|---|---|
| `backend_config` | Backend configuration for the run step (required) |
| `processor` | Postprocessor configuration (required) |
| `process_kwargs` | Extra keyword arguments for `postprocess()` |
| `cleanup_on_failure` | Delete the workspace if the run fails (default `False`) |
| `validate_stages` | Check that the workspace exists after generating (default `True`) |

The pipeline stops at the first failing step. `results["success"]` is then `False`, `results["stage"]` names the step and `results["message"]` says what failed. A postprocessor that reports failure is logged but does not stop the pipeline.

### Pipeline files

`rompy pipeline` reads one YAML file with three sections: `config` (the `ModelRun`), `backend` and `postprocessor`. Each section can be written inline or pulled from another file with `!include`, which lets several pipelines share backend and postprocessor files. Include paths are relative to the including file.

```python exec="on" source="above" result="text" session="backends"
from rompy.backends import LocalConfig
from rompy.core.yaml_loader import load_yaml_with_includes
from rompy.postprocess.config import NoopPostprocessorConfig

folder = OUT_DIR / "pipeline"
(folder / "backends").mkdir(parents=True)
(folder / "backends" / "local.yml").write_text("type: local\ncommand: ls > files.txt\n")
(folder / "pipeline.yml").write_text(f"""
config:
  run_id: from-yaml
  output_dir: {OUT_DIR}
  period: {{start: "2023-01-01", end: "2023-01-02", interval: 1h}}
  config: {{model_type: base}}
backend: !include backends/local.yml
postprocessor:
  type: noop
""")

data = load_yaml_with_includes(folder / "pipeline.yml")
print(data["backend"])
```

The command line then builds the three objects, as here, and calls `pipeline()`:

```python exec="on" source="above" result="text" session="backends"
backend_data = dict(data["backend"])
backend = BACKENDS[backend_data.pop("type")](**backend_data)
processor_data = dict(data["postprocessor"])
processor_data.pop("type")
processor = NoopPostprocessorConfig(**processor_data)

run = ModelRun(**data["config"])
results = run.pipeline(backend_config=backend, processor=processor)
print(results["stages_completed"])
```

```bash
rompy pipeline pipeline.yml
rompy pipeline pipeline.yml --backend-config backends/docker.yml   # replace the backend section
```

## See also

- [The run lifecycle](run-lifecycle.md): where running fits.
- [Backend internals](../development/backend-internals.md): writing a backend, postprocessor or pipeline backend.
- Notebooks: [backend examples](https://rom-py.github.io/rompy-notebooks/notebooks/backends/backend_examples/), [running XBeach](https://rom-py.github.io/rompy-notebooks/notebooks/xbeach/examples/running_xbeach/), [running SWAN](https://rom-py.github.io/rompy-notebooks/notebooks/swan/examples/running_swan/).
- Reference: [run backends](../reference/backends.md), [postprocessors](../reference/postprocess.md), [pipelines](../reference/pipeline.md).
