# write pydantic model to read xarray data from intake catalogs, filter, and write to netcdf

import os
import pathlib
from typing import Optional

import cloudpathlib
import intake
import xarray as xr
from pydantic import root_validator

from .filters import Filter
from .types import RompyBaseModel

# from .filters import lonlat_filter, time_filter, variable_filter


class DataBlob(RompyBaseModel):
    """Data source for model ingestion. This is intended to be a generic data source
    for files that simply need to be copied to the model directory.

    Must be a local file or a remote file.

    Parameters
    ----------
    id: str
            Unique identifier for this data source
    path: str
          Optional local file path
    url: str
            Optional remote file url


    """

    id: str
    path: Optional[pathlib.Path]
    url: Optional[cloudpathlib.CloudPath]

    @root_validator
    def check_path_or_url(cls, values):
        if values.get("path") is None and values.get("url") is None:
            raise ValueError("Must provide either a path or a url")
        if values.get("path") is not None and values.get("url") is not None:
            raise ValueError("Must provide either a path or a url, not both")
        return values

    def get(self, dest: str) -> "DataBlob":
        """Copy the data source to a new location"""
        if self.path:
            pathlib.Path(dest).write_bytes(self.path.read_bytes())
        elif self.url:
            pathlib.Path(dest).write_bytes(self.url.read_bytes())
        return DataBlob(id=self.id, path=dest)


class DataGrid(RompyBaseModel):
    """Data source for model ingestion. This is intended to be a generic data source
    for xarray datasets that need to be filtered and written to netcdf.

    Must be a local file (path) or a remote file (url) or intake and dataset id combination.

    Parameters
    ----------
    id: str
            Unique identifier for this data source
    path: str
            Optional local file path
    url: str
            Optional remote file url
    catalog: str
            Optional intake catalog
    dataset: str
            Optional intake dataset id
    params: dict
            Optional parameters to pass to the intake catalog
    filter: Filter
            Optional filter specification to apply to the dataset
    xarray_kwargs: dict
            Optional keyword arguments to pass to xarray.open_dataset
    netcdf_kwargs: dict
            Optional keyword arguments to pass to xarray.Dataset.to_netcdf

    """

    id: str
    path: Optional[pathlib.Path]
    url: Optional[cloudpathlib.CloudPath]
    catalog: Optional[str]  # TODO make this smarter
    dataset: Optional[str]
    args: Optional[dict] = {}
    params: Optional[dict] = {}
    filter: Optional[Filter] = Filter()
    latname: Optional[str] = "latitude"
    lonname: Optional[str] = "longitude"
    timename: Optional[str] = "time"
    xarray_kwargs: Optional[dict] = {}
    netcdf_kwargs: Optional[dict] = dict(mode="w", format="NETCDF4")

    @root_validator
    def check_path_or_url_or_intake(cls, values):
        if values.get("path") is None and values.get("url") is None:
            if values.get("catalog") is None or values.get("dataset") is None:
                raise ValueError(
                    "Must provide either a path or a url or a catalog and dataset"
                )
        if (
            values.get("path") is not None
            and values.get("url") is not None
            and values.get("catalog") is not None
        ):
            raise ValueError("Must provide only one of a path url or catalog")
        return values

    def _filter_grid(self, grid, start=None, end=None, buffer=0.1):
        """Define the filters to use to extract data to this grid"""
        minLon, minLat, maxLon, maxLat = grid.bbox()
        self.filter.crop = {
            self.lonname: slice(minLon - buffer, maxLon + buffer),
            self.latname: slice(minLat - buffer, maxLat + buffer),
            self.timename: slice(start, end),
        }

    @property
    def ds(self):
        """Return the xarray dataset for this data source."""
        if self.path:
            ds = xr.open_dataset(self.path, **self.xarray_kwargs)
        elif self.url:
            ds = xr.open_dataset(self.url, **self.xarray_kwargs)
        elif self.catalog:
            cat = intake.open_catalog(self.catalog)
            ds = cat[self.dataset](**self.args, **self.params).to_dask()
        if self.filter:
            ds = self.filter(ds)
        return ds

    def get(self, stage_dir: str) -> "DataGrid":
        """Write the data source to a new location"""
        dest = os.path.join(stage_dir, f"{self.id}.nc")
        self.ds.to_netcdf(dest, **self.netcdf_kwargs)
        return DataGrid(id=self.id, path=dest, **self.netcdf_kwargs)
