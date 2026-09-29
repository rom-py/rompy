# Time

Every run has a period: when the model starts, when it stops, and the interval of its time steps or outputs. rompy represents it with [`TimeRange`][rompy.core.time.TimeRange], shared by all models.

## Defining a period

A `TimeRange` takes two of `start`, `end` and `duration`, and computes the third. `interval` sets the spacing of the times in the range (one hour by default).

```python exec="on" source="above" result="text" session="time"
from rompy.core.time import TimeRange

by_end = TimeRange(start="2023-01-01T00", end="2023-01-02T00", interval="6h")
by_duration = TimeRange(start="2023-01-01T00", duration="1d", interval="6h")
backwards = TimeRange(end="2023-01-02T00", duration="PT12H", interval="PT3H")

print(by_end.end == by_duration.end, by_duration.duration)
print(backwards.start)
```

Giving only one of the three, or all three, is an error.

Values can be given as:

| Field | Accepted values |
|---|---|
| `start`, `end` | `datetime` objects, ISO strings such as `"2023-01-01T06:00"`, and compact forms such as `"20230101"`, `"20230101T06"` and `"20230101.060000"` |
| `duration`, `interval` | `timedelta` objects, ISO 8601 durations such as `"PT6H"` or `"P1D"`, or a number and a unit: `s`, `m` (minutes), `h`, `d`, `w` |

!!! warning "`M` means minutes"
    In the short form, `m` and `M` both mean minutes, so `"15M"` is 15 minutes, not 15 months. Months and years are not supported in either form (`"P1M"` and `"P1Y"` are rejected); give long periods in days or weeks.

## The times in a period

`date_range` lists the times from `start` to `end` at `interval`:

```python exec="on" source="above" result="text" session="time"
for time in by_end.date_range:
    print(time)
```

`include_end` (true by default) adds `end` to the list even when it does not fall on the interval. Set it to false to keep only the times on the interval:

```python exec="on" source="above" result="text" session="time"
uneven = TimeRange(start="2023-01-01T00", end="2023-01-01T10", interval="4h")
print([t.hour for t in uneven.date_range])

uneven = TimeRange(start="2023-01-01T00", end="2023-01-01T10", interval="4h", include_end=False)
print([t.hour for t in uneven.date_range])
```

## Comparing periods

`contains` tests a time, `contains_range` another period, and `common_times` returns the times of this range that fall within another one:

```python exec="on" source="above" result="text" session="time"
from datetime import datetime

print(by_end.contains(datetime(2023, 1, 1, 12)))
print(by_end.contains_range(backwards))
print([str(t) for t in by_end.common_times(backwards)])
```

## In YAML

A period is a mapping with the same fields, in the same forms as in Python:

```python exec="on" source="above" result="text" session="time"
import yaml

text = """
start: 2023-01-01T00:00
end: 2023-01-02T00:00
interval: 6h
"""
period = TimeRange(**yaml.safe_load(text))
print(period == by_end)
```

When a period is written out, `duration` is dropped if `start` and `end` are both set, and intervals become ISO durations:

```python exec="on" source="above" result="text" session="time"
print(yaml.safe_dump(by_end.model_dump(mode="json"), sort_keys=False))
```

## How models use the period

The period is set once, on [`ModelRun.period`][rompy.model.ModelRun], and everything else takes it from there:

- **Templates** receive it as `runtime.period`, so a template can write the start, stop and time step in the model's own format (see [Your first run](../getting-started/first-run.md)).
- **Data objects** receive it in `get(destdir, grid, time)` and crop their source to it, optionally with some extra source time steps either side (`time_buffer`). See [Data and sources](data.md).
- **Model plugins** turn it into the model's time settings: rompy-xbeach sets XBeach's stop time `tstop` from its duration; rompy-swan uses it for the times of its `COMPUTE` and output commands.

Plugin configurations take the period from the run rather than holding their own copy, so the same configuration can be generated for different periods by changing `ModelRun.period` only.
