import os
from pathlib import Path
import tempfile
from datetime import datetime

import numpy as np
import pandas as pd
import pytest
import xarray as xr

import rompy
from rompy.core.filters import Filter
from rompy.core.data import DatasetCoords
from rompy.core import (
    BaseGrid,
    DataBlob,
    DataGrid,
    Dataset,
    DatasetIntake,
    DatasetXarray,
    DatasetDatamesh,
    TimeRange,
)


HERE = Path(__file__).parent
DATAMESH_TOKEN = os.environ.get("DATAMESH_TOKEN")


# create dummy local datasource for testing
@pytest.fixture
def txt_data_source():
    # touch temp text file
    tmp_path = tempfile.mkdtemp()
    source = os.path.join(tmp_path, "test.txt")
    with open(source, "w") as f:
        f.write("hello world")
    return DataBlob(id="test", path=source)


@pytest.fixture
def grid_data_source():
    return DataGrid(
        id="wind",
        catalog=os.path.join(rompy.__path__[0], "catalogs", "oceanum.yaml"),
        dataset="era5_wind10m",
        filter={
            "sort": {"coords": ["latitude"]},
            "crop": {
                "time": slice("2000-01-01", "2000-01-02"),
                "latitude": slice(0, 10),
                "longitude": slice(0, 10),
            },
        },
    )


def test_get(txt_data_source):
    ds = txt_data_source
    output = ds.get("./test.txt")
    assert output.path.is_file()


def test_get_no_path(txt_data_source):
    ds = txt_data_source
    with pytest.raises(TypeError):
        ds.get()


def test_fails_both_path_and_url():
    with pytest.raises(ValueError):
        DataBlob(path="foo", url="bar")


@pytest.mark.skip(reason="not reproducible outside of oceanum")
def test_intake_grid(grid_data_source):
    data = grid_data_source
    assert data.ds.latitude.max() == 10
    assert data.ds.latitude.min() == 0
    assert data.ds.longitude.max() == 10
    assert data.ds.longitude.min() == 0
    downloaded = data.get("simulations")
    assert downloaded.ds.latitude.max() == 10
    assert downloaded.ds.latitude.min() == 0
    assert downloaded.ds.longitude.max() == 10
    assert downloaded.ds.longitude.min() == 0


@pytest.fixture
def nc_data_source():
    # touch temp netcdf file
    tmp_path = tempfile.mkdtemp()
    source = os.path.join(tmp_path, "test.nc")
    ds = xr.Dataset(
        {
            "data": xr.DataArray(
                np.random.rand(10, 10, 10),
                dims=["time", "latitude", "longitude"],
                coords={
                    "time": pd.date_range("2000-01-01", periods=10),
                    "latitude": np.arange(0, 10),
                    "longitude": np.arange(0, 10),
                },
            )
        }
    )
    ds.to_netcdf(source)
    return DataGrid(id="grid", dataset=DatasetXarray(dataset=source))


def test_netcdf_grid(nc_data_source):
    data = nc_data_source
    assert data.ds.latitude.max() == 9
    assert data.ds.latitude.min() == 0
    assert data.ds.longitude.max() == 9
    assert data.ds.longitude.min() == 0


def test_grid_filter(nc_data_source):
    grid = BaseGrid(x=np.arange(2, 7), y=np.arange(3, 7))
    nc_data_source._filter_grid(grid)
    assert nc_data_source.ds.latitude.max() == 6
    assert nc_data_source.ds.latitude.min() == 3
    assert nc_data_source.ds.longitude.max() == 6
    assert nc_data_source.ds.longitude.min() == 2


def test_grid_filter_buffer(nc_data_source):
    grid = BaseGrid(x=np.arange(3, 7), y=np.arange(3, 7))
    nc_data_source._filter_grid(grid, buffer=1)
    assert nc_data_source.ds.latitude.max() == 7
    assert nc_data_source.ds.latitude.min() == 2
    assert nc_data_source.ds.longitude.max() == 7
    assert nc_data_source.ds.longitude.min() == 2


def test_time_filter(nc_data_source):
    grid = BaseGrid(x=np.arange(3, 7), y=np.arange(3, 7))
    nc_data_source._filter_grid(grid, buffer=1)
    nc_data_source._filter_time(TimeRange(start="2000-01-02", end="2000-01-03"))
    assert nc_data_source.ds.latitude.max() == 7
    assert nc_data_source.ds.latitude.min() == 2
    assert nc_data_source.ds.longitude.max() == 7
    assert nc_data_source.ds.longitude.min() == 2
    assert nc_data_source.ds.time.max() == np.datetime64("2000-01-03")
    assert nc_data_source.ds.time.min() == np.datetime64("2000-01-02")


def test_dataset():
    dset = xr.open_dataset(HERE / "data" / "aus-20230101.nc")
    dataset = Dataset(dataset=dset)
    assert isinstance(dataset.open(), xr.Dataset)


def test_dataset_xarray():
    dataset = DatasetXarray(dataset=HERE / "data" / "aus-20230101.nc")
    assert isinstance(dataset.open(), xr.Dataset)


def test_dataset_intake():
    dataset = DatasetIntake(
        dataset="ausspec",
        catalog_uri=HERE / "data" / "catalog.yaml",
    )
    assert isinstance(dataset.open(), xr.Dataset)


@pytest.mark.skipif(DATAMESH_TOKEN is None, reason="Datamesh token required")
def test_dataset_datamesh():
    dataset = DatasetDatamesh(dataset="era5_wind10m", token=DATAMESH_TOKEN)
    filters = Filter()
    filters.crop.update(dict(time=slice("2000-01-01T00:00:00", "2000-01-01T03:00:00")))
    filters.crop.update(
        dict(longitude=slice(115.5, 116.0), latitude=slice(-33.0, -32.5))
    )
    dset = dataset.open(variables=["u10"], filters=filters, coords=DatasetCoords(x="longitude", y="latitude"))
    assert(isinstance(dset, xr.Dataset))