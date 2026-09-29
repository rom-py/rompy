# Contributing

Contributions are welcome: bug reports and ideas as [GitHub issues](https://github.com/rom-py/rompy/issues), and changes as pull requests. Please follow the [Code of Conduct](https://github.com/rom-py/rompy/blob/main/CODE_OF_CONDUCT.rst).

Changes to how a particular model is configured belong in that model's plugin: [rompy-xbeach](https://github.com/rom-py/rompy-xbeach), [rompy-swan](https://github.com/rom-py/rompy-swan) or [rompy-schism](https://github.com/rom-py/rompy-schism). rompy holds what every model shares: the run, time, grids, data and sources, rendering, backends and the command line.

## Development setup

rompy needs Python 3.10 or later.

```bash
git clone https://github.com/YOUR-USERNAME/rompy.git
cd rompy
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pre-commit install
```

The `dev` extra installs pytest, coverage, ruff, black and respx. Add `extra` (`pip install -e ".[dev,extra]"`) for the cloud storage and zarr dependencies.

## Tests and style

```bash
pytest                                # the test suite
black src tests                       # format (the pre-commit hook runs black --check)
ruff check src tests                  # lint
```

Code is formatted with black at a line length of 88. [Testing](testing.md) describes the test suite and how to write tests.

## Where things go

rompy is extended through entry points, so most additions are a class plus a line in `pyproject.toml`:

| To add | Subclass | Entry point group |
|---|---|---|
| A model configuration | [`BaseConfig`][rompy.core.config.BaseConfig] | `rompy.config` |
| A data source | [`SourceBase`][rompy.core.source.SourceBase] | `rompy.source` |
| A run backend | [`BaseBackendConfig`][rompy.backends.config.BaseBackendConfig] and a backend class | `rompy.run` |
| A postprocessor | [`BasePostprocessorConfig`][rompy.postprocess.config.BasePostprocessorConfig] and a postprocessor class | `rompy.postprocess.config`, `rompy.postprocess` |
| A pipeline backend | a class with `execute()` | `rompy.pipeline` |
| A file transfer scheme | [`TransferBase`][rompy.transfer.base.TransferBase] | `rompy.transfer` |

[Backend internals](backend-internals.md) explains how backends, postprocessors and pipeline backends are found and called.

## Building the docs

The docs are built with [ProperDocs](https://github.com/ProperDocs/properdocs) (a maintained fork of MkDocs), Material and mkdocstrings, using the configuration shared by all rompy sites in [rompy-docs](https://github.com/rom-py/rompy-docs):

```bash
pip install -e ".[docs,test]"
python -c "import tests.conftest"           # download the example data into tests/data
properdocs serve -f mkdocs.yml              # live preview
properdocs build --strict -f mkdocs.yml     # what CI runs
rompy-docs check -f mkdocs.yml              # compare with the shared configuration
```

- **The reference is generated** from the docstrings and Pydantic field descriptions. The docstring style is detected per docstring, so numpy and Google style both work; keep to the style of the module you are editing.
- **Examples run when the docs are built.** Write examples in docstrings and pages as markdown-exec blocks; a failing example fails the strict build. Use a plain `python` block only for examples that need a model executable, Docker or remote data.

    ````markdown
    ```python exec="on" source="above" result="text" session="time"
    from rompy.core.time import TimeRange

    print(TimeRange(start="2023-01-01", end="2023-01-02", interval="6h"))
    ```
    ````

- **Link classes** to the reference with `` [`ModelRun`][rompy.model.ModelRun] ``. Broken links fail the strict build.
- **Tutorials and examples** live in [rompy-notebooks](https://github.com/rom-py/rompy-notebooks) and are published at [rom-py.github.io/rompy-notebooks](https://rom-py.github.io/rompy-notebooks/); link to them rather than copying them here.

## Pull requests

1. Create a branch from `main`.
2. Make the change, with tests and docs.
3. Run `pytest`, the formatter and the strict docs build.
4. Open a pull request that says what changed and why, and reference the issue it fixes (e.g. "Fixes #123").

A maintainer reviews the change; once approved it is merged. Contributors are listed in [AUTHORS.rst](https://github.com/rom-py/rompy/blob/main/AUTHORS.rst).

## License

rompy is released under the [Apache License 2.0](https://github.com/rom-py/rompy/blob/main/LICENSE). By contributing, you agree that your contributions are licensed under the same license.
