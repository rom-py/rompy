# Pipeline Command Migration Guide

## Overview

The `rompy pipeline` command has been redesigned to support a cleaner, more consistent configuration structure with YAML include functionality.

## What Changed

### Old Structure (Deprecated)

```bash
# Separate files required
rompy pipeline model.yaml \
  --run-backend local \
  --processor-config processor.yaml
```

**Problems with old approach:**
- `--run-backend` only accepted type string ("local", "docker")
- No way to configure backend timeout, commands, or environment variables
- Mandatory separate processor config file
- Inconsistent with `rompy run` command structure

### New Structure

```bash
# All-in-one pipeline config
rompy pipeline pipeline.yaml

# Or with overrides
rompy pipeline pipeline.yaml \
  --backend-config custom_backend.yaml \
  --processor-config custom_processor.yaml
```

**Benefits:**
- Single file for complete workflows
- Full backend configuration support
- Optional inline or referenced configs
- YAML `!include` directives for composition
- Consistent nested structure

## New Config Structure

All pipeline configs must now use this three-section structure:

```yaml
config:           # ModelRun configuration
  run_id: my_run
  period:
    start: "2023-01-01T00:00:00"
    end: "2023-01-02T00:00:00"
  config:
    model_type: shel
    # ... model-specific config

backend:          # Backend configuration
  type: local     # or docker, slurm
  timeout: 7200
  command: ./run.sh
  env_vars:
    VAR: value

postprocessor:    # Postprocessor configuration
  type: ww3_transfer
  destinations:
    - "file:///backup/"
  timeout: 3600
```

## YAML Include Support

### Basic Include

Compose configs from multiple files:

```yaml
config: !include model_config.yaml
backend: !include backends/local.yaml
postprocessor: !include postprocessors/transfer.yaml
```

### Mixed Inline and Includes

```yaml
config: !include shared/global_model.yaml

backend:
  type: local
  timeout: 7200

postprocessor: !include postprocessors/ww3_transfer.yaml
```

### Include Features

- **Relative paths**: Resolved from the including file's directory
- **Absolute paths**: Supported
- **Environment variables**: `!include $HOME/configs/backend.yaml`
- **Nested includes**: Includes can reference other includes
- **Circular detection**: Prevents infinite loops
- **Depth limit**: Maximum 10 levels of nesting

## Migration Examples

### Example 1: Basic Migration

**Old:**
```bash
# model.yaml
run_id: test
period: {...}
config: {...}

# Command
rompy pipeline model.yaml \
  --run-backend local \
  --processor-config proc.yaml
```

**New:**
```yaml
# pipeline.yaml
config:
  run_id: test
  period: {...}
  config: {...}

backend:
  type: local

postprocessor: !include proc.yaml
```

```bash
rompy pipeline pipeline.yaml
```

### Example 2: With Backend Options

**Old (not possible):**
```bash
# Could NOT configure timeout or custom commands
rompy pipeline model.yaml --run-backend local --processor-config proc.yaml
```

**New:**
```yaml
config: !include model.yaml

backend:
  type: local
  timeout: 7200
  command: ./custom_run.sh
  env_vars:
    OMP_NUM_THREADS: "4"

postprocessor: !include proc.yaml
```

### Example 3: Modular Configs

**Organize by environment:**
```
configs/
├── models/
│   ├── global_3deg.yaml
│   └── regional_1deg.yaml
├── backends/
│   ├── local_dev.yaml
│   ├── local_prod.yaml
│   └── docker.yaml
├── postprocessors/
│   ├── transfer_s3.yaml
│   └── transfer_local.yaml
└── pipelines/
    ├── dev_pipeline.yaml
    └── prod_pipeline.yaml
```

**dev_pipeline.yaml:**
```yaml
config: !include ../models/global_3deg.yaml
backend: !include ../backends/local_dev.yaml
postprocessor: !include ../postprocessors/transfer_local.yaml
```

**prod_pipeline.yaml:**
```yaml
config: !include ../models/global_3deg.yaml
backend: !include ../backends/local_prod.yaml
postprocessor: !include ../postprocessors/transfer_s3.yaml
```

## CLI Override Behavior

CLI flags override inline configurations:

```yaml
# pipeline.yaml
config: {...}
backend:
  type: local
  timeout: 3600
postprocessor:
  type: noop
```

```bash
# Override backend
rompy pipeline pipeline.yaml --backend-config docker_backend.yaml

# Override postprocessor
rompy pipeline pipeline.yaml --processor-config custom_proc.yaml

# Override both
rompy pipeline pipeline.yaml \
  --backend-config docker_backend.yaml \
  --processor-config custom_proc.yaml
```

## Breaking Changes

### Removed

1. **`--run-backend` flag** - Replaced with nested `backend` config or `--backend-config`
2. **Flat config structure** - All configs must now use nested `config`/`backend`/`postprocessor` sections

### Required Changes

| Old | New |
|-----|-----|
| `--run-backend local` | `backend: {type: local}` in config or `--backend-config` |
| `--processor-config FILE` (required) | `postprocessor:` in config or `--processor-config` (optional) |
| Top-level `run_id`, `period` | Nest under `config:` section |

## Error Messages

### Missing Sections

```
Error: Pipeline config must contain 'config' section with ModelRun configuration.
```
**Fix:** Wrap your model config in a `config:` section.

```
Error: Backend configuration required. Provide either:
  - 'backend' section in pipeline config, or
  - --backend-config flag
```
**Fix:** Add `backend:` section or use `--backend-config`.

```
Error: Postprocessor configuration required. Provide either:
  - 'postprocessor' section in pipeline config, or
  - --processor-config flag
```
**Fix:** Add `postprocessor:` section or use `--processor-config`.

### Include Errors

```
Error: Included file not found: configs/model.yaml
Referenced from: /path/to/pipeline.yaml
```
**Fix:** Check the file path is correct relative to the including file.

```
Error: Circular include detected: /path/to/file1.yaml
Include chain: file1.yaml -> file2.yaml -> file1.yaml
```
**Fix:** Remove circular references in your includes.

## Backward Compatibility

**None.** This is a breaking change. The old `--run-backend` string flag is no longer supported.

All existing pipeline commands must be updated to use the new structure.

## Best Practices

1. **Use includes for reusability**: Keep backend and postprocessor configs in separate files for reuse
2. **Environment-specific configs**: Create separate pipeline files for dev/staging/prod
3. **Validate early**: Use `rompy pipeline --help` to see expected structure
4. **Keep model configs portable**: Model configs (`config:` section) should not contain backend/processor details
5. **Version control**: Commit all config files including referenced includes

## Examples

See the `examples/` directory for complete working examples:

- `global_3deg_pipeline.yaml` - All inline configuration
- `global_3deg_pipeline_with_includes.yaml` - Using !include directives

## Questions?

- Run `rompy pipeline --help` for command documentation
- Check existing tests: `tests/test_yaml_loader.py` for include examples
- See `src/rompy/core/yaml_loader.py` for include implementation details
