# Documenting a plugin

The rompy documentation is a set of sites read as one resource: this site for the concepts, one site per model plugin for its guide and reference, and the notebook site for tutorials and examples. A model plugin's site follows a shared template, so readers find the same things in the same places whichever model they use. [rompy-xbeach](https://rom-py.github.io/rompy-xbeach/) is the reference implementation; copy its structure and configuration when starting a new site.

| Layer | Site | Contents |
|---|---|---|
| Concepts | [rompy](https://rom-py.github.io/rompy/) | Why rompy, the objects every model shares, writing plugins |
| Guide and reference | one per model, e.g. [rompy-xbeach](https://rom-py.github.io/rompy-xbeach/) | How the model maps to rompy, its settings, its API |
| Learn | [rompy-notebooks](https://rom-py.github.io/rompy-notebooks/) | Tutorials and examples, rendered with their outputs |

## Page structure of a model site

Every model site has the same sections, in this order. `‹…›` marks the parts that depend on the model.

```text
Home                          what the model is, what rompy-‹model› adds, a short example, where to go next
Getting started
  Installation                pip and extras; the model executable; the Docker image and its tags
  Your first model            a minimal config → generate → run; links to tutorial lesson 1
User guide
  How rompy-‹model› works     how the config maps to the model's input files; what comes from rompy
  Configuration               Python and YAML, the CLI, validation and model-specific checks
  ‹Grid›                      e.g. grid and bathymetry, CGRID and INPGRID, mesh and vertical grid
  ‹Forcing and boundaries›    one page per forcing: waves, tide and water level, wind, ...
  ‹Model settings›            e.g. physics, sediment, numerics, namelist groups
  Output
  Running ‹model›             backends, Docker image, MPI, checking a run
  Hotstart and chained runs
  Troubleshooting             model-specific gotchas
Tutorial                      generated from the notebook inventory
Examples                      generated from the notebook inventory
Reference
  Config, components, data interfaces, sources, types (one page per group)
  Parameter index             generated: model parameter → field, type, default
Development
  Contributing, Changelog
```

Rules that keep the sites consistent:

- **Each object is rendered once**, with `:::` on its Reference page. Guide pages link to it, e.g. ``[`Physics`][rompy_xbeach.components.physics.physics.Physics]``, and never render it again.
- **Every example that can run, runs** (see [Executed examples](#executed-examples)). Only examples that need data that is not in the repository, a model executable or Docker stay static.
- **rompy objects are linked, not re-explained.** A guide page says what the model does with a [`DataGrid`][rompy.core.data.DataGrid] and links to rompy's reference and concept pages for the rest.
- **Guide pages end with a "See it in the notebooks" box**, generated from the notebook inventory (see [Linking notebooks](#linking-notebooks)).

## The shared tooling: rompy-docs

[rompy-docs](https://github.com/rom-py/rompy-docs) holds what the sites share: the build stack, the theme files, the `mkdocs.yml` template and helpers. Add it to the package's `docs` extra:

```toml
[project.optional-dependencies]
docs = ["rompy-docs @ git+https://github.com/rom-py/rompy-docs.git"]
```

Installing it installs ProperDocs, Material for MkDocs, mkdocstrings, griffe-pydantic and markdown-exec at compatible versions. Then:

1. Copy the blocks of rompy-docs' `template.yml` into the site's `mkdocs.yml`, and add the site's own `site_name`, `site_url`, repository, `nav` and:

    ```yaml
    extra:
      rompy:
        site: xbeach   # rompy, xbeach, swan, schism or notebooks
    ```

2. Run `rompy-docs sync` to copy the theme files (the bar linking all the sites and the shared stylesheet) into `docs/`, and commit them.
3. Build with `properdocs build --strict -f mkdocs.yml`. In CI, also run `rompy-docs check`, which reports where the site's configuration or theme files differ from the template.

| Command | What it does |
|---|---|
| `rompy-docs sync [-f mkdocs.yml]` | Copies the shared theme files into the site's docs folder |
| `rompy-docs check [-f mkdocs.yml]` | Compares the site with the template; exits with 1 on a difference |
| `rompy-docs convert PATHS [--check]` | Rewrites Sphinx `.. ipython:: python` and `.. code-block::` directives in docstrings as Markdown fences |

## API reference with inherited fields

The template renders pydantic models with [griffe-pydantic](https://mkdocstrings.github.io/griffe-pydantic/): each class lists its fields with their types, defaults and descriptions. Two settings make the fields a class inherits from rompy appear too, such as `template` and `checkout` on a configuration or `source` and `filter` on a data interface:

```yaml
plugins:
  - mkdocstrings:
      handlers:
        python:
          paths: [src]
          inventories:
            - url: !ENV [ROMPY_INVENTORY, "https://rom-py.github.io/rompy/objects.inv"]
              base_url: https://rom-py.github.io/rompy/
          options:
            preload_modules: [rompy]
```

- **`preload_modules: [rompy]`** loads rompy's classes so that griffe can show the inherited fields. Model sites must set it; the rompy site must not, and `rompy-docs check` checks both.
- **The rompy inventory** makes links such as ``[`ModelRun`][rompy.model.ModelRun]`` resolve to this site. `ROMPY_INVENTORY` points a local build at the inventory of an unpublished rompy site.

The template also applies `rompy_docs.griffe:PydanticFieldRules`, which applies pydantic's rules for what is a field (no leading underscore, an annotation) that griffe-pydantic's static mode misses, so private and unannotated attributes are not listed as fields.

## Executed examples

Examples in docstrings and pages are [markdown-exec](https://pawamoy.github.io/markdown-exec/) blocks. The code runs when the docs are built and its printed output is shown below it. With `--strict`, the build fails when an example raises, so the docs build also tests the examples.

In a numpy-style docstring, the block goes in the `Examples` section, with one `session` per docstring:

````python
class GEN3(BaseComponent):
    """Third generation physics.

    Examples
    --------
    ```python exec="on" source="above" result="text" session="gen3"
    from rompy_swan.components.physics import GEN3
    print(GEN3().render())
    ```

    """
````

On pages, use one session per page, and create files only in a temporary folder made in a hidden setup block (a block without `source=`, so nothing is shown). Examples that need data that is not in the repository, a model executable or Docker are plain ```` ```python ```` blocks. `rompy-docs convert` turns existing Sphinx examples into these blocks; review the diff, since examples that were never run may fail.

## Linking notebooks

Notebooks are rendered only on the [notebook site](https://rom-py.github.io/rompy-notebooks/). Model sites link to them with the helpers in `rompy_docs.notebooks`, which read the inventory the notebook site publishes, so the lists stay current without copying notebooks.

| Helper | Use it on | Print it from |
|---|---|---|
| `tutorial_table(model)` | The Tutorial page: the ordered lessons, as a Markdown table | ```` ```python exec="on" ```` |
| `cards(model, kind="example")` | The Examples page: one card per notebook | ```` ```python exec="on" html="1" ```` |
| `see_also(model, topics)` | The end of a guide page: the notebooks on those topics | ```` ```python exec="on" ```` |

For example, the end of rompy-xbeach's wind page:

````markdown
```python exec="on"
from rompy_docs.notebooks import see_also

print(see_also("xbeach", ["wind", "forcing"]))
```
````

`ROMPY_NOTEBOOKS_INVENTORY` points a build at a local inventory file or another URL, to build against an unpublished notebook collection.

## A checklist for a new model site

1. Add `rompy-docs` to the `docs` extra; copy `template.yml` into `mkdocs.yml`; set `extra.rompy.site`, `preload_modules: [rompy]` and the rompy inventory.
2. Run `rompy-docs sync`, then `rompy-docs check` until it reports no differences.
3. Write the pages in the structure above, starting from [rompy-xbeach's](https://rom-py.github.io/rompy-xbeach/), with [How rompy-xbeach works](https://rom-py.github.io/rompy-xbeach/user-guide/how-it-works/) as the model for the "How it works" page.
4. Convert docstring examples with `rompy-docs convert` and make them run.
5. Generate the Tutorial and Examples pages and the "See it in the notebooks" boxes from the notebook inventory.
6. Build with `properdocs build --strict` in CI.
