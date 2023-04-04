import os
import tempfile

import numpy as np
import pandas as pd
import pytest
import xarray as xr

import rompy
from rompy.data import DataBlob, DataGrid


# create dummy local datasource for testing
@pytest.fixture
def txt_data_source():
    # touch temp text file
    tmp_path = tempfile.mkdtemp()
    source = os.path.join(tmp_path, "test.txt")
    with open(source, "w") as f:
        f.write("hello world")
    return DataBlob(path=source)


def test_stage(txt_data_source):
    ds = txt_data_source
    output = ds.stage("./test.txt")
    assert output.path.is_file()


def test_stage_no_path(txt_data_source):
    ds = txt_data_source
    with pytest.raises(TypeError):
        ds.stage()


def test_fails_both_path_and_url():
    with pytest.raises(ValueError):
        DataBlob(path="foo", url="bar")


@pytest.fixture
def grid_data_source():
    return DataGrid(
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


@pytest.mark.skip(reason="not reproducible outside of oceanum")
def test_intake_grid(grid_data_source):
    data = grid_data_source
    assert data.ds.latitude.max() == 10
    assert data.ds.latitude.min() == 0
    assert data.ds.longitude.max() == 10
    assert data.ds.longitude.min() == 0


# create netcdf data with latitude, longitude, time, and data variables for testing
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
                    "latitude": np.linspace(0, 10, 10),
                    "longitude": np.linspace(0, 10, 10),
                },
            )
        }
    )
    ds.to_netcdf(source)
    return DataGrid(path=source)


def test_netcdf_grid(nc_data_source):
    data = nc_data_source
    assert data.ds.latitude.max() == 10
    assert data.ds.latitude.min() == 0
    assert data.ds.longitude.max() == 10
    assert data.ds.longitude.min() == 0
