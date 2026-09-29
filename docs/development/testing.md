# Testing

rompy is tested with pytest. Every change should come with tests: a new feature with tests of what it does, a bug fix with a test that fails without the fix.

## Running the tests

Install the development dependencies first (`pip install -e ".[dev]"`), then from the repository root:

```bash
pytest                                  # everything
pytest tests/test_time.py               # one file
pytest tests/test_time.py::test_name    # one test
pytest -k "backend"                     # tests whose names match
```

Coverage:

```bash
coverage run -m pytest
coverage report -m
```

Two options are added by `tests/conftest.py`:

| Option | Effect |
|---|---|
| `--run-slow` | Also run tests that are skipped by default because they are slow or need remote data |
| `--rompy-log-level LEVEL` | Log level during the tests (default `INFO`) |

### Test data

The data files in `tests/data/` (NetCDF, CSV and intake catalogs) are not in the repository. The first time the tests run with an empty or missing `tests/data/`, `conftest.py` downloads them from the latest release of [rompy-test-data](https://github.com/rom-py/rompy-test-data), so the first run needs network access.

### Docker

The tests in `tests/integration/` run containers and are skipped when Docker is not available.

## Layout

| Path | Contents |
|---|---|
| `tests/test_*.py` | Tests of the core modules: time, grids, data, sources, templates, templating, YAML loading, transfers |
| `tests/backends/` | Backend configurations and the local, Docker and SLURM backends (mocked) |
| `tests/core/` | Logging |
| `tests/integration/` | Runs in Docker |
| `tests/simulations/` | Reference workspaces that generated files are compared with |
| `tests/test_helpers.py` | `DemoConfig`, a small configuration for tests |
| `tests/utils/`, `tests/test_utils/` | File comparison and logging helpers |

## Writing tests

Test each validator both ways, with a value it accepts and one it rejects:

```python
import pytest
from pydantic import ValidationError

from rompy.backends import LocalConfig


def test_local_config_timeout():
    assert LocalConfig(timeout=600).timeout == 600
    with pytest.raises(ValidationError, match="greater than or equal to 60"):
        LocalConfig(timeout=30)
```

Generate into pytest's `tmp_path` and compare the files with a reference, as `tests/test_templates.py` does:

```python
from rompy.model import ModelRun
from tests.test_helpers import DemoConfig
from tests.utils import compare_files


def test_generate(tmp_path):
    run = ModelRun(
        run_id="test_base",
        output_dir=tmp_path,
        config=DemoConfig(arg1="foo", arg2="bar"),
    )
    workspace = run.generate()
    assert workspace == tmp_path / "test_base"
    compare_files(workspace / "INPUT", "tests/simulations/test_base_ref/INPUT")
```

`compare_files` skips lines starting with `$`, which hold the generation time and user.

A local backend can run a shell command, so the run step can be tested without a model:

```python
from rompy.backends import LocalConfig


def test_run(tmp_path):
    run = ModelRun(run_id="run", output_dir=tmp_path)
    workspace = run.generate()
    assert run.run(LocalConfig(command="touch done"), workspace_dir=workspace)
    assert (workspace / "done").exists()
```

To test code that calls a backend without running anything, patch the backend class:

```python
from unittest.mock import patch


def test_run_calls_backend(tmp_path):
    run = ModelRun(run_id="run", output_dir=tmp_path)
    with patch("rompy.run.LocalRunBackend.run", return_value=True) as backend_run:
        assert run.run(LocalConfig(command="xbeach"))
    backend_run.assert_called_once()
```

Test the command line with click's test runner:

```python
from click.testing import CliRunner

from rompy.cli import cli


def test_validate(tmp_path):
    config = tmp_path / "run.yml"
    config.write_text("run_id: cli\nconfig:\n  model_type: base\n")
    result = CliRunner().invoke(cli, ["validate", str(config)])
    assert result.exit_code == 0
```

Read test data from `tests/data/`:

```python
from rompy.core.source import SourceFile


def test_source_file():
    ds = SourceFile(uri="tests/data/era5-20230101.nc").open()
    assert "u10" in ds
```

Mock HTTP requests with respx (in the `dev` extra) instead of reaching the network; `tests/test_transfer_http.py` has examples.

## See also

- [Contributing](contributing.md).
