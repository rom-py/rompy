# Template Variable Substitution

Rompy supports template variable substitution in YAML configuration files using `${VAR}` syntax. This allows you to:

- Use environment variables in configs
- Set default values for missing variables
- Process datetime values with filters
- Share configs across different environments

## Syntax

### Basic Substitution

```yaml
output_dir: "${OUTPUT_ROOT}/my_run"
run_id: "${RUN_ID}"
```

### Default Values

Provide fallback values when variables are not set:

```yaml
output_dir: "${OUTPUT_ROOT:-./output}/my_run"
timeout: "${JOB_TIMEOUT:-3600}"
threads: "${NUM_THREADS:-4}"
```

### Type Conversion

When a YAML value is **exactly** one template expression, type conversion is automatic:

```yaml
timeout: "${TIMEOUT}"          # "3600" → 3600 (int)
debug: "${DEBUG}"               # "true" → True (bool)
pi: "${PI}"                     # "3.14" → 3.14 (float)
```

Embedded templates always produce strings:

```yaml
path: "/data/${USER}/file"     # Always string
```

## Datetime Filters

### Available Filters

| Filter | Description | Example |
|--------|-------------|---------|
| `as_datetime` | Parse ISO-8601 datetime | `${CYCLE\|as_datetime}` |
| `strftime` | Format datetime | `${CYCLE\|strftime:%Y%m%d}` |
| `shift` | Add/subtract time | `${CYCLE\|shift:-1d}` |

### Filter Chaining

Combine filters with `|`:

```yaml
previous_day: "${CYCLE|as_datetime|shift:-1d|strftime:%Y-%m-%d}"
```

### Datetime Examples

```yaml
cycle_date: "${CYCLE|as_datetime}"
filename: "wind_${CYCLE|strftime:%Y%m%d}.nc"
prev_cycle: "${CYCLE|as_datetime|shift:-1d}"
end_time: "${CYCLE|as_datetime|shift:+24h}"
```

### Shift Syntax

Time deltas use: `[+|-]<number><unit>`

Units:
- `d` = days
- `h` = hours
- `m` = minutes
- `s` = seconds

Examples:
- `+1d` = add 1 day
- `-6h` = subtract 6 hours
- `+30m` = add 30 minutes

## Complete Examples

### Basic Config

```yaml
run_id: "cycle_${CYCLE|strftime:%Y%m%d}"

period:
  start: "${CYCLE}"
  end: "${CYCLE|as_datetime|shift:+1d}"
  interval: "1H"

output_dir: "${OUTPUT_ROOT:-./output}/cycle_${CYCLE|strftime:%Y%m%d}"

input_files:
  wind: "${DATA_ROOT}/wind/wind_${CYCLE|strftime:%Y%m%d}.nc"
  wave: "${DATA_ROOT}/wave/wave_${CYCLE|strftime:%Y%m%d}.nc"
```

Usage:
```bash
export CYCLE=2023-01-01T00:00:00
export DATA_ROOT=/scratch/data
rompy generate config.yml
```

### Backend Config

```yaml
type: local
timeout: "${JOB_TIMEOUT:-3600}"
command: "python run_model.py"

env_vars:
  OMP_NUM_THREADS: "${NUM_THREADS:-4}"
  WORK_DIR: "${WORK_DIR}"
```

Usage:
```bash
export WORK_DIR=/scratch/my_job
export NUM_THREADS=8
rompy run config.yml --backend-config backend.yml
```

### Lookback Pattern

Access previous time periods:

```yaml
input_files:
  current: "${DATA_ROOT}/data_${CYCLE|strftime:%Y%m%d}.nc"
  previous: "${DATA_ROOT}/data_${CYCLE|as_datetime|shift:-1d|strftime:%Y%m%d}.nc"
  week_ago: "${DATA_ROOT}/data_${CYCLE|as_datetime|shift:-7d|strftime:%Y%m%d}.nc"
```

### Nested Directory Structures

```yaml
output_dir: "${DATA_ROOT}/output/${CYCLE|strftime:%Y/%m/%d}"
```

With `CYCLE=2023-01-15T00:00:00` → `/data/output/2023/01/15`

## How It Works

Template rendering happens **after YAML parsing** but **before Pydantic validation**:

```
1. Load YAML file → dict
2. Render templates: ${VAR} → actual values
3. Pydantic validation: dict → ModelRun object
```

This ensures:
- Type safety (Pydantic sees resolved values)
- Clear error messages (template errors before validation errors)
- Datetime objects work with Pydantic models

## Error Handling

### Missing Variables

By default, missing variables cause an error:

```yaml
path: "${MISSING_VAR}"  # Error: Variable 'MISSING_VAR' not found
```

Use defaults to make variables optional:

```yaml
path: "${OPTIONAL_VAR:-/default/path}"  # OK if OPTIONAL_VAR not set
```

### Invalid Filters

Unknown filters produce clear errors:

```yaml
date: "${CYCLE|unknown_filter}"  # Error: Unknown filter 'unknown_filter'
```

### Datetime Parsing

Invalid datetime strings fail early:

```yaml
date: "${CYCLE|as_datetime}"  # Error if CYCLE is not ISO-8601 format
```

## Tips

### Quote Values with `:-`

YAML interprets `:` as mapping syntax. Quote defaults containing colons:

```yaml
path: "${VAR:-/path/with:colon}"  # GOOD - quoted
path: ${VAR:-/path/with:colon}    # BAD - YAML parse error
```

### Environment Variables

Templates use `os.environ` by default:

```bash
export MY_VAR=value
rompy generate config.yml  # ${MY_VAR} resolved automatically
```

### Separation from Jinja2

Don't confuse with rompy's existing Jinja2 templates (used for model control files):

- `${VAR}` = **Config templating** (pre-load, env vars)
- `{{runtime.var}}` = **File templating** (post-load, Python objects)

They serve different purposes and run at different times.

## See Also

- Example configs: `examples/configs/templated_*.yml`
- Tests: `tests/test_templating.py`
- Implementation: `src/rompy/templating.py`
