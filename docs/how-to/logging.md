# Logging and output formatting

rompy logs what it does through Python's `logging` module, with a shared configuration and helpers that draw boxes, lists and status messages. This page shows how to control the output and how plugins use the same tools.

```python exec="on" session="logging"
# Hidden setup: send log records to a buffer so that they can be shown on this page.
import io
import logging

from rompy.logging import config as logging_config

BUFFER = io.StringIO()
CAPTURE = logging.StreamHandler(BUFFER)
CAPTURE.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))


def capture_log():
    logging_config.update(level="INFO", format="standard")
    logging_config.configure_logging()
    root = logging.getLogger()
    for handler in root.handlers[:]:
        root.removeHandler(handler)
    root.addHandler(CAPTURE)


def show_log():
    print(BUFFER.getvalue().rstrip())
    BUFFER.seek(0)
    BUFFER.truncate()
```

## Making rompy quieter or more verbose

The logging configuration is one object, `rompy.logging.config`. Change it with `update()`, which reconfigures the handlers straight away:

```python
from rompy.logging import config

config.update(level="WARNING")   # only warnings and errors, e.g. in a notebook
config.update(level="DEBUG")     # everything
```

| Setting | Default | Environment variable | Meaning |
|---|---|---|---|
| `level` | `INFO` | `ROMPY_LEVEL` | `DEBUG`, `INFO`, `WARNING`, `ERROR` or `CRITICAL` |
| `format` | `verbose` | `ROMPY_FORMAT` | `simple`, `standard` or `verbose`, see below |
| `log_dir` | none | `ROMPY_LOG_DIR` | Also write the log to a file in this folder |
| `log_file` | `rompy.log` | `ROMPY_LOG_FILE` | Name of that file |
| `use_ascii` | `False` | `ROMPY_USE_ASCII` | Draw boxes and symbols with ASCII characters |

The environment variables are read when rompy is imported, and also from a `.env` file in the current folder. The class docstring of [`LoggingConfig`][rompy.logging.config.LoggingConfig] calls the first two `ROMPY_LOG_LEVEL` and `ROMPY_LOG_FORMAT`; the names read are `ROMPY_LEVEL` and `ROMPY_FORMAT`.

| Format | A line looks like |
|---|---|
| `simple` | `Rendering model configurations` |
| `standard` | `INFO: Rendering model configurations` |
| `verbose` | `2023-01-01 12:00:00 [INFO] rompy.model          : Rendering model configurations` |

!!! warning "Use update(), not LoggingConfig()"
    `LoggingConfig` is a singleton: creating `LoggingConfig()` returns the same object and resets it to the defaults and environment variables, without reconfiguring the handlers. Some of rompy's own formatting helpers do this, so a setting made with `update()` can be reset later. Settings that must last, `use_ascii` in particular, are best set with environment variables.

### On the command line

The `rompy` command sets the level and format from its options, whatever the environment says: warnings only by default, `-v` for INFO, `-vv` for DEBUG, and `--simple-logs` for the simple format. `--log-dir` (or `ROMPY_LOG_DIR`) adds a log file, and `--ascii-only` (or `ROMPY_ASCII_ONLY`) switches to ASCII. See [The command line](cli.md#options-for-every-command).

## Logging from a plugin

Use [`get_logger`][rompy.logging.logger.get_logger] with the module name. It returns a standard logger with a few extra methods, and it follows the shared configuration:

```python exec="on" session="logging"
capture_log()
```

```python exec="on" source="above" result="text" session="logging"
from rompy.logging import BoxStyle, get_logger

logger = get_logger("mymodel.boundary")

logger.info("Reading wave spectra")
logger.success("Boundary written")
logger.warning("No wind data, using calm conditions")
logger.error("Spectra do not cover the run period")
logger.bullet_list(["bnd.txt", "spectra/001.sp2"])
logger.box("nx = 115\nny = 110", title="Grid")
logger.status_box("All inputs written", BoxStyle.SUCCESS)
logger.debug("Not shown at INFO level")
show_log()
```

`success()`, `warning()` and `error()` prefix the message with a symbol; `box()`, `status_box()` and `bullet_list()` log one line per line of the drawing.

## Formatting helpers

The drawings are also available as text, from `rompy.logging` and [`rompy.formatting`][rompy.formatting]:

```python exec="on" source="above" result="text" session="logging"
from rompy.formatting import format_table_row, get_formatted_box
from rompy.logging import box, bullet_list

print(box("Hs = 1.5 m\nTp = 10 s", title="Waves"))
print(bullet_list(["params.txt", "bed.dep"]))
print(get_formatted_box("MODEL GENERATION COMPLETE", width=40))
print(format_table_row("Run ID", "demo"))
```

[`log_box`][rompy.formatting.log_box] logs a title box of the kind [`ModelRun.generate`][rompy.model.ModelRun.generate] prints between its steps, and [`log_horizontal_line`][rompy.formatting.log_horizontal_line] logs a separator.

With `use_ascii`, the same helpers draw with ASCII characters, for terminals and log files that do not show Unicode. The `rompy.formatting` functions also take `use_ascii` as an argument:

```python exec="on" source="above" result="text" session="logging"
logging_config.update(use_ascii=True)
print(box("Hs = 1.5 m", title="Waves"))
logging_config.update(use_ascii=False)

print(get_formatted_box("DONE", width=20, use_ascii=True))
```

## How objects print

rompy objects print as an indented tree of their fields, which is what `generate()` logs for the model configuration:

```python exec="on" source="above" result="text" session="logging"
from rompy.core.time import TimeRange
from rompy.core.types import RompyBaseModel


class Forcing(RompyBaseModel):
    name: str
    period: TimeRange
    variables: list[str]


forcing = Forcing(
    name="era5",
    period=TimeRange(start="2023-01-01", end="2023-01-02", interval="1h"),
    variables=["u10", "v10"],
)
print(forcing)
```

A class can change how particular values are shown by overriding `_format_value`, which returns text for the values it handles and `None` for the rest. The default formats paths, datetimes and time deltas:

```python exec="on" source="above" result="text" session="logging"
from datetime import datetime


class Cycle(RompyBaseModel):
    cycle: datetime

    def _format_value(self, obj):
        if isinstance(obj, datetime):
            return obj.strftime("%Y-%m-%d %HZ")
        return super()._format_value(obj)


print(Cycle(cycle="2023-01-01T06:00"))
```

```python exec="on" session="logging"
# Hidden: restore the logging configuration for the rest of the site.
logging.getLogger().removeHandler(CAPTURE)
logging_config.update(level="WARNING", format="verbose", use_ascii=False)
logging_config.configure_logging()
```

## See also

- Reference: [logging and formatting](../reference/logging.md).
