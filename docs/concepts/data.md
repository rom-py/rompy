# Data and sources

A model needs bathymetry, winds, waves, water levels and other inputs, which come from datasets in many formats, far larger than the model domain and period. In rompy, an input is described as a **request**: which source to read, which variables, what the coordinates are called and how to transform them. The request is resolved only when the workspace is generated, for the model's grid and period.

```text
source + variables + filters + (grid, period)
                     |
                     v
       only the slice the run needs
                     |
                     v
          file in the model workspace
```

The run description holds the request, not the data. It stays small, can be versioned and shared, and a colleague can regenerate the same inputs from the same sources, or point it at a local copy.

```python exec="on" session="data"
# Hidden setup: quiet logging and a temporary output folder.
import tempfile
from pathlib import Path

from rompy.logging import config as logging_config

logging_config.update(level="WARNING")
OUT_DIR = Path(tempfile.mkdtemp())
```

## Two layers: sources and data objects

rompy separates two concerns:

- A **source** knows how to open one kind of dataset (a netCDF file, an intake catalogue, a Datamesh datasource, wave spectra, a CSV file) and returns an xarray dataset.
- A **data object** holds a source and says what the model needs from it: variables, coordinate names, filters, and how to cut it to the grid and period. Its `get` method writes the result into the workspace.

The same data object can take a different source, as long as the new source provides the same variables and coordinates.

| Data object | For | `get` writes |
|---|---|---|
| [`DataBlob`][rompy.core.data.DataBlob] | Any file, used as is | A copy of (or link to) the file |
| [`DataPoint`][rompy.core.data.DataPoint] | Time series at a point | The series cut to the period |
| [`DataGrid`][rompy.core.data.DataGrid] | Gridded fields | The fields cut to the grid's bounding box and the period |
| [`DataBoundary`][rompy.core.boundary.DataBoundary] | Gridded fields along the grid outline | Values at points along the outline |
| [`BoundaryWaveStation`][rompy.core.boundary.BoundaryWaveStation] | Wave spectra at stations | Spectra at points along the outline |

Model plugins subclass these to write the model's own formats: rompy-xbeach's bathymetry and forcing classes are `DataGrid` subclasses, rompy-swan's `SwanDataGrid` writes SWAN input grids and `Boundnest1` extends `BoundaryWaveStation`.

## Files as they are: DataBlob

[`DataBlob`][rompy.core.data.DataBlob] copies a file into the workspace, or links to it with `link=True`. [`DataBlob.get`][rompy.core.data.DataBlob.get] returns the new path, which is also kept in `copied_path`:

```python exec="on" source="above" result="text" session="data"
from rompy.core.data import DataBlob

blob = DataBlob(id="wind_csv", source="tests/data/wind.csv")
print(blob.copied_path)

path = blob.get(OUT_DIR)
print(path.name, blob.copied_path == path)

linked = DataBlob(source="tests/data/wind.csv", link=True)
print(linked.get(OUT_DIR, name="wind_linked.csv").is_symlink())
```

`source` is a path or a URI: a local path, `s3://`, `gs://` or `az://` cloud storage, an `http(s)://` URL, or `oceanum://` storage. Remote files are downloaded through the [transfer subsystem](#remote-files-and-transfers). Only local files can be linked:

```python exec="on" source="above" result="text" session="data"
from pydantic import ValidationError

try:
    DataBlob(source="https://example.com/bathy.nc", link=True)
except ValidationError as err:
    print(err.errors()[0]["msg"])
```

## Gridded data: DataGrid

[`DataGrid`][rompy.core.data.DataGrid] reads gridded fields. This one asks for the 10 m winds in a small ERA5 file:

```python exec="on" source="above" result="text" session="data"
from rompy.core.data import DataGrid
from rompy.core.filters import Filter
from rompy.core.source import SourceFile

wind = DataGrid(
    id="wind",
    source=SourceFile(uri="tests/data/era5-20230101.nc"),
    variables=["u10", "v10"],
    coords={"x": "longitude", "y": "latitude", "t": "time"},
    filter=Filter(sort={"coords": ["latitude"]}),
    buffer=5.0,
)
print(dict(wind.source.open().sizes))
```

Nothing is read until the data is needed. [`DataGrid.get`][rompy.core.data.DataGrid.get] takes the destination folder, the grid and the period, crops the source to them and writes `<id>.nc`:

```python exec="on" source="above" result="text" session="data"
import xarray as xr

from rompy.core.grid import RegularGrid
from rompy.core.time import TimeRange

grid = RegularGrid(x0=110.0, y0=-35.0, dx=5.0, dy=5.0, nx=4, ny=3)
period = TimeRange(start="2023-01-01T00", end="2023-01-01T12", interval="6h")

outfile = wind.get(OUT_DIR, grid=grid, time=period)
extracted = xr.open_dataset(outfile)
print(outfile.name, dict(extracted.sizes))
print("longitude:", extracted.longitude.values)
print("latitude: ", extracted.latitude.values)
```

The fields that shape the request:

| Field | Purpose |
|---|---|
| `source` | Where the data comes from; see [Sources](#sources) |
| `variables` | The variables to keep (all when empty) |
| `coords` | Names of the time (`t`), x, y, and optionally z and site (`s`) coordinates in the source |
| `filter` | Transformations applied after reading; see [Filters](#filters) |
| `crop_data` | Whether `get` crops to the grid and period (true by default) |
| `buffer` | Extra distance around the grid's bounding box, in the grid's units |
| `time_buffer` | Extra source time steps before and after the period, as `[before, after]` |

When cropping, `get` adds the crop to the object's filter, so `wind.filter` now holds the ranges used:

```python exec="on" source="above" result="text" session="data"
for name, window in wind.filter.crop.items():
    print(name, window.start, "to", window.stop)
```

!!! warning "Sort descending coordinates"
    Cropping selects coordinate ranges from low to high. Many datasets, ERA5 among them, store latitudes from north to south, and a crop then returns nothing:

    ```python exec="on" source="above" result="text" session="data"
    source = SourceFile(uri="tests/data/era5-20230101.nc")
    crop = {"latitude": slice(-40, -20)}
    print(dict(source.open(filters=Filter(crop=crop)).sizes))
    print(dict(source.open(filters=Filter(sort={"coords": ["latitude"]}, crop=crop)).sizes))
    ```

    Add a `sort` filter for such coordinates, as in the `wind` object above.

## Time series: DataPoint

[`DataPoint`][rompy.core.data.DataPoint] is for data with time as the only dimension, such as a wind or water level record. It crops to the period only. Its source must be a time series source, such as a CSV file read by [`SourceTimeseriesCSV`][rompy.core.source.SourceTimeseriesCSV]:

```python exec="on" source="above" result="text" session="data"
from rompy.core.data import DataPoint
from rompy.core.source import SourceTimeseriesCSV

station = DataPoint(
    id="wind_station",
    source=SourceTimeseriesCSV(filename="tests/data/wind.csv"),
    variables=["wspd", "wdir"],
)
series = xr.open_dataset(station.get(OUT_DIR, time=period))
print(list(series.data_vars), series.time.values[0], "to", series.time.values[-1])
```

## Boundary data

A boundary object selects data at points along the outline of the grid, for models that need boundary conditions there. The points come from the grid's `boundary_points` (see [Grids](grids.md)): the corners by default, or points every `spacing` along the outline; `spacing="parent"` uses the resolution of the source.

[`DataBoundary`][rompy.core.boundary.DataBoundary] does this for gridded fields, selecting with xarray's `sel` (the default, which needs exact coordinate matches unless `sel_method_kwargs={"method": "nearest"}`) or `interp` (`sel_method`):

```python exec="on" source="above" result="text" session="data"
from rompy.core.boundary import DataBoundary

wind_boundary = DataBoundary(
    id="wind_boundary",
    source=SourceFile(uri="tests/data/era5-20230101.nc"),
    variables=["u10", "v10"],
    coords={"x": "longitude", "y": "latitude"},
    filter=Filter(sort={"coords": ["latitude"]}),
    spacing=5.0,
    sel_method="interp",
)
points = xr.open_dataset(wind_boundary.get(OUT_DIR, grid=grid, time=period))
print(dict(points.sizes))
```

[`BoundaryWaveStation`][rompy.core.boundary.BoundaryWaveStation] does it for wave spectra stored at stations, as in the output of a regional wave model. It selects with [wavespectra](https://wavespectra.readthedocs.io/): inverse distance weighting of the nearest stations (`idw`, the default) or the nearest station (`nearest`), within a `tolerance` in degrees:

```python exec="on" source="above" result="text" session="data"
from rompy.core.boundary import BoundaryWaveStation
from rompy.core.source import SourceWavespectra

coastal_grid = RegularGrid(x0=113.0, y0=-34.0, dx=0.5, dy=0.5, nx=4, ny=6)
waves = BoundaryWaveStation(
    id="waves",
    source=SourceWavespectra(uri="tests/data/aus-20230101.nc", reader="read_netcdf"),
    spacing=0.5,
    sel_method="idw",
    sel_method_kwargs={"tolerance": 2.0},
)
spectra = xr.open_dataset(waves.get(OUT_DIR, grid=coastal_grid, time=period))
print(dict(spectra.sizes))
```

With `idw`, points with too few stations within `tolerance` get missing values; with `nearest`, a point with no station within `tolerance` is an error.

## Sources

| Source | `model_type` | Reads | Main fields |
|---|---|---|---|
| [`SourceFile`][rompy.core.source.SourceFile] | `file` | Any file xarray can open | `uri`, `kwargs` for `xarray.open_dataset`, `variable` to return one variable |
| [`SourceIntake`][rompy.core.source.SourceIntake] | `intake` | A dataset in an [intake](https://intake.readthedocs.io/) catalogue | `dataset_id`, and `catalog_uri` or `catalog_yaml`, `kwargs` for the dataset's parameters |
| [`SourceDatamesh`][rompy.core.source.SourceDatamesh] | `datamesh` | A datasource on Oceanum [Datamesh](https://docs.oceanum.io/datamesh/index.html) | `datasource`, `token` (default from the environment), `kwargs` for the connector |
| [`SourceWavespectra`][rompy.core.source.SourceWavespectra] | `wavespectra` | Wave spectra, with a wavespectra reader | `uri`, `reader` (e.g. `read_swan`, `read_ww3`), `kwargs` |
| [`SourceTimeseriesCSV`][rompy.core.source.SourceTimeseriesCSV] | `csv` | A time series in a CSV file | `filename`, `tcol` (time column), `read_csv_kwargs` |

An intake catalogue gives datasets names, so the run description does not depend on where the files are:

```python exec="on" source="above" result="text" session="data"
from rompy.core.source import SourceIntake

catalogued = SourceIntake(dataset_id="era5", catalog_uri="tests/data/catalog.yaml")
print(list(catalogued.open().data_vars))
```

`SourceDatamesh` differs from the others: it turns the crop filter into a query, so only the requested area and period are downloaded. It needs a Datamesh token, from the `token` field or the `DATAMESH_TOKEN` environment variable:

```python
from rompy.core.source import SourceDatamesh

wind = DataGrid(
    id="wind",
    source=SourceDatamesh(datasource="my_wind_datasource"),
    variables=["u10", "v10"],
    coords={"x": "longitude", "y": "latitude"},
)
```

### Plugin sources

Sources are plugins, registered in the `rompy.source` entry point group, and a data object's `source` field accepts every registered source by its `model_type`. rompy registers its own sources this way; a package adds more in its `pyproject.toml`:

```toml
[project.entry-points."rompy.source"]
file = "rompy.core.source:SourceFile"
"csv:timeseries" = "rompy.core.source:SourceTimeseriesCSV"
```

The `:timeseries` suffix marks sources that return time series; [`DataPoint`][rompy.core.data.DataPoint] accepts only those. A new source subclasses [`SourceBase`][rompy.core.source.SourceBase], sets its own `model_type` and implements `_open()` to return an xarray dataset. Model plugins can also keep their own source groups; rompy-xbeach, for example, adds sources with a coordinate reference system.

## Filters

A [`Filter`](../reference/filters.md) transforms the dataset after it is read. It has one field per operation, always applied in this order:

| Field | Operation | Example |
|---|---|---|
| `sort` | Sort by coordinates | `{"coords": ["latitude"]}` |
| `subset` | Keep some variables | `{"data_vars": ["u10", "v10"]}` |
| `crop` | Select coordinate ranges | `{"time": slice("2023-01-01", "2023-01-02")}` |
| `timenorm` | Replace time by lead time from the first (or a reference) time | `{"interval": "hour"}` |
| `rename` | Rename variables or coordinates | `{"u10": "uwnd"}` |
| `derived` | Add variables computed from others | `{"derived_variables": {"wspd": "(ds.uwnd**2 + ds.vwnd**2) ** 0.5"}}` |

The expressions in `derived` are Python, evaluated with the dataset as `ds`, so only load configurations with derived variables from sources you trust.

```python exec="on" source="above" result="text" session="data"
wind_speed = DataGrid(
    id="wind_speed",
    source=SourceFile(uri="tests/data/era5-20230101.nc"),
    variables=["u10", "v10"],
    coords={"x": "longitude", "y": "latitude"},
    filter=Filter(
        sort={"coords": ["latitude"]},
        rename={"u10": "uwnd", "v10": "vwnd"},
        derived={"derived_variables": {"wspd": "(ds.uwnd**2 + ds.vwnd**2) ** 0.5"}},
    ),
)
fields = xr.open_dataset(wind_speed.get(OUT_DIR, grid=grid, time=period))
print(list(fields.data_vars))
```

## Remote files and transfers

Files are moved in and out of workspaces by the transfer subsystem, [`rompy.transfer`](../reference/transfer.md). Each URI scheme has a transfer class, registered in the `rompy.transfer` entry point group:

```python exec="on" source="above" result="text" session="data"
from rompy.transfer.registry import get_registry
from rompy.transfer.utils import parse_scheme

for scheme, transfer in sorted(get_registry().items()):
    print(f"{scheme:8s} {transfer.__name__}")

print(parse_scheme("tests/data/wind.csv"), parse_scheme("s3://bucket/bathy.nc"))
```

| Scheme | Access | Credentials |
|---|---|---|
| `file` (plain paths) | Local files; copy or link | |
| `http`, `https` | Download only, with retries; a file already in the destination is not downloaded again | |
| `s3`, `gs`, `az` | Cloud storage through [cloudpathlib](https://cloudpathlib.drivendata.org/); install `rompy[extra]` for the cloud clients | The provider's usual environment variables, e.g. `AWS_ACCESS_KEY_ID`, `GOOGLE_APPLICATION_CREDENTIALS`, `AZURE_STORAGE_CONNECTION_STRING` |
| `oceanum` | Oceanum storage | `DATAMESH_TOKEN` |

[`get_transfer`][rompy.transfer.registry.get_transfer] returns the transfer for a URI, and `DataBlob` uses it, so a remote file is fetched in the same way as a local one:

```python
bathy = DataBlob(id="bathy", source="s3://my-bucket/bathy/perth.nc")
bathy.get(workspace)  # downloads perth.nc into the workspace
```

To copy results out to several places at once, [`TransferManager`][rompy.transfer.manager.TransferManager] sends each file to a list of destination prefixes and reports each transfer:

```python
from pathlib import Path

from rompy.transfer import TransferManager

files = [Path("run/output.nc")]
result = TransferManager().transfer_files(
    files=files,
    destinations=["s3://my-bucket/runs/", "/archive/runs/"],
    name_map={files[0]: "20230101_output.nc"},
)
print(result.succeeded, result.failed)
```

A package can add a scheme by registering a subclass of [`TransferBase`][rompy.transfer.base.TransferBase] under the scheme's name in the `rompy.transfer` group.

## What stays with the modeller

Selecting data on demand makes the choices explicit, not correct. Whether a dataset suits the question, which variables and coordinates are meant, how to interpolate and what to do with gaps remain modelling decisions. Record where the data came from, look at the generated inputs, and validate the model setup for the experiment.

## See it in the notebooks

- XBeach: [bathymetry](https://rom-py.github.io/rompy-notebooks/notebooks/xbeach/tutorial/03_bathymetry/), [forcing](https://rom-py.github.io/rompy-notebooks/notebooks/xbeach/tutorial/04_forcing/), [data sources](https://rom-py.github.io/rompy-notebooks/notebooks/xbeach/examples/data_sources/) and [data selection options](https://rom-py.github.io/rompy-notebooks/notebooks/xbeach/examples/data_selection/).
- SWAN: [input grids](https://rom-py.github.io/rompy-notebooks/notebooks/swan/tutorial/03_input_grids/) and [wave boundaries](https://rom-py.github.io/rompy-notebooks/notebooks/swan/tutorial/04_wave_boundaries/), selected from a regional wave model.
- SCHISM: [forcing](https://rom-py.github.io/rompy-notebooks/notebooks/schism/tutorial_04_schism_forcing/) on an unstructured mesh.
- The [rompy hands-on notebook](https://rom-py.github.io/rompy-notebooks/notebooks/common/rompy_hands_on/) extracts winds for a toy model and plots the result.
