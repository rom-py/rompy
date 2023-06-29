"""Rompy core data objects."""
import logging
import os
import json
from pathlib import Path
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Literal, Optional

from cloudpathlib import CloudPath
import intake
from intake.catalog import Catalog
import xarray as xr
from pydantic import Field, root_validator
from oceanum.datamesh import Connector, Query
import geopandas
from shapely.geometry import Polygon

from .filters import Filter
from .time import TimeRange
from .types import RompyBaseModel


logger = logging.getLogger(__name__)


class Coords(RompyBaseModel):
    """Coordinates representation."""
    t: Optional[str] = Field("time", description="Name of the time coordinate")
    x: Optional[str] = Field("longitude", description="Name of the x coordinate")
    y: Optional[str] = Field("latitude", description="Name of the y coordinate")
    z: Optional[str] = Field("depth", description="Name of the z coordinate")


class DataBlob(RompyBaseModel):
    """Data source for model ingestion.

    This is intended to be a generic data source for files that simply need to be
    copied to the model directory.

    TODO: If we are happy to support cloudpathlib here than we could use
    cloudlib.AnyPath and only have say URI parameter.

    """

    id: str = Field(description="Unique identifier for this data source")
    path: Optional[Path] = Field(
        default=None, description="Optional local file path"
    )
    url: Optional[CloudPath] = Field(
        default=None, description="Optional remote file url"
    )

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
            Path(dest).write_bytes(self.path.read_bytes())
        elif self.url:
            Path(dest).write_bytes(self.url.read_bytes())
        return DataBlob(id=self.id, path=dest)


class Dataset(RompyBaseModel):
    """Dataset input base class.

    This is the base dataset class to provide an xarray Dataset object to the DataGrid.
    It is intended to be subclassed by other dataset classes that can deal with
    different types of data sources such as intake, datamesh or xarray. It can also
    be used directly if a Dataset object is already available.

    """
    model_type: Literal["dataset"] = Field(
        default="dataset",
        description="Model type discriminator",
    )
    dataset: xr.Dataset = Field(
        description="xarray Dataset object",
    )

    class Config:
        arbitrary_types_allowed = True

    def __str__(self) -> str:
        return f"Dataset(dataset={self.dataset})"

    def _open(self) -> xr.Dataset:
        """Returns the xarray dataset.

        This is a private method that should be implemented by subclasses.

        """
        return self.dataset

    def open(self, variables: list = [], filters: Filter = {}, **kwargs) -> xr.Dataset:
        """Return the filtered dataset object.

        Parameters
        ----------
        variables : list, optional
            List of variables to select from the dataset.
        filters : Filter, optional
            Filters to apply to the dataset.

        Notes
        -----
        The kwargs are only a placeholder in case a subclass needs to pass additional
        arguments to the open method.

        """
        ds = self._open()
        if variables:
            ds = ds[variables]
        if filters:
            ds = filters(ds)
        return ds


class DatasetXarray(Dataset):
    """Dataset input from xarray reader."""

    model_type: Literal["xarray"] = Field(
        default="xarray",
        description="Model type discriminator",
    )
    dataset: str | Path = Field(description="Path to the xarray dataset")
    engine: Optional[str] = Field(
        default=None,
        description="Engine to use for reading the dataset with xarray.open_dataset",
    )
    kwargs: Optional[dict] = Field(
        default={},
        description="Keyword arguments to pass to xarray.open_dataset",
    )

    def __str__(self) -> str:
        return f"DatasetXarray(dataset={self.dataset})"

    def _open(self) -> xr.Dataset:
        return xr.open_dataset(self.dataset, engine=self.engine, **self.kwargs)


class DatasetIntake(Dataset):
    """Dataset from intake catalog."""

    model_type: Literal["intake"] = Field(
        default="intake",
        description="Model type discriminator",
    )
    dataset: str = Field(
        description="The id of the dataset to read in the intake catalog",
    )
    catalog_uri: str | Path = Field(
        description="The URI of the catalog to read from",
    )
    kwargs: dict = Field(
        default={},
        description="Keyword arguments to pass to intake.open_catalog",
    )

    def __str__(self) -> str:
        return f"DatasetIntake(catalog_uri={self.catalog_uri}, dataset={self.dataset})"

    @property
    def cat(self) -> Catalog:
        """Returns the intake catalog instance."""
        return intake.open_catalog(self.catalog_uri)

    def _open(self) -> xr.Dataset:
        return self.cat[self.dataset](**self.kwargs).to_dask()


class DatasetDatamesh(Dataset):
    """Dataset from Datamesh.

    Datamesh documentation: https://docs.oceanum.io/datamesh/index.html

    """

    model_type: Literal["datamesh"] = Field(
        default="datamesh",
        description="Model type discriminator",
    )
    dataset: str = Field(
        description="The id of the dataset on Datamesh",
    )
    token: Optional[str] = Field(
        description="The Datamesh API token, taken from the environment if not provided",
    )
    kwargs: dict = Field(
        default={},
        description="Keyword arguments to pass to `oceanum.datamesh.Connector`",
    )

    def __str__(self) -> str:
        return f"DatasetDatamesh(dataset={self.dataset})"

    @property
    def connector(self) -> Connector:
        """The Datamesh connector instance."""
        return Connector(token=self.token, **self.kwargs)

    def _geofilter(self, filters, coords) -> dict:
        """The Datamesh geofilter."""
        xslice = filters.crop.get(coords.x)
        yslice = filters.crop.get(coords.y)
        if xslice is None or yslice is None:
            logger.warning(
                f"No slices found for x={coords.x} and y={coords.y} in the crop "
                f"filter {filters.crop}, cannot define a geofilter for querying"
            )
            return None

        coords = [
            [xslice.start, yslice.start],
            [xslice.stop, yslice.start],
            [xslice.stop, yslice.stop],
            [xslice.start, yslice.stop],
            [xslice.start, yslice.start],
        ]
        geofilter = dict(
            type="feature",
            geom=dict(
                type="Feature",
                geometry=dict(
                    type="Polygon",
                    coordinates=[coords],
                ),
             ),
        )
        return geofilter

    def _timefilter(self, filters, coords) -> dict:
        """The Datamesh timefilter."""
        tslice = filters.crop.get(coords.t)
        if tslice is None:
            logger.warning(
                f"No time slice found in the crop filter {filters.crop}, "
                "cannot define a timefilter for querying datamesh"
            )
            return None
        timefilter = dict(
            type="range",
            times=[tslice.start, tslice.stop],
        )
        return timefilter

    def open(
        self,
        filters: Filter,
        coords: Coords,
        variables: list = []
    ) -> xr.Dataset:
        """Returns the filtered dataset object.

        Override this method to allow providing geo and time filters for query.

        """
        query = dict(
            datasource=self.dataset,
            variables=variables,
            geofilter=self._geofilter(filters, coords),
            timefilter=self._timefilter(filters, coords),
        )
        ds = self.connector.query(query)
        if filters:
            ds = filters(ds)
        return ds


class DataGrid(RompyBaseModel):
    """Data source for model ingestion. This is intended to be a generic data
    source for xarray datasets that need to be filtered and written to netcdf.

    """

    id: str = Field(description="Unique identifier for this data source")
    dataset: DatasetXarray | DatasetIntake | DatasetDatamesh = Field(
        description="Dataset reader, must return an xarray dataset in the open method",
        discriminator="model_type",
    )
    filter: Optional[Filter] = Field(
        Filter(), description="Optional filter specification to apply to the dataset"
    )
    variables: Optional[list[str]] = Field(
        [], description="Subset of variables to extract from the dataset"
    )
    coords: Optional[Coords] = Field(
        default=Coords(),
        description="Names of the coordinates in the dataset",
    )

    def _filter_grid(self, grid, buffer=0.1):
        """Define the filters to use to extract data to this grid"""
        minLon, minLat, maxLon, maxLat = grid.bbox()
        self.filter.crop.update(
            {
                self.coords.x: slice(minLon - buffer, maxLon + buffer),
                self.coords.y: slice(minLat - buffer, maxLat + buffer),
            }
        )

    def _filter_time(self, time: TimeRange):
        """Define the filters to use to extract data to this grid"""
        self.filter.crop.update(
            {
                self.coords.t: slice(time.start, time.end),
            }
        )

    @property
    def ds(self):
        """Return the xarray dataset for this data source."""
        ds = self.dataset.open(
            variables=self.variables, filters=self.filter, coords=self.coords
        )
        return ds

    def plot(self, param, isel={}, model_grid=None, cmap="turbo", fscale=10, **kwargs):
        """Plot the grid"""

        import cartopy.crs as ccrs
        import cartopy.feature as cfeature
        import matplotlib.pyplot as plt
        from cartopy.mpl.gridliner import LATITUDE_FORMATTER, LONGITUDE_FORMATTER

        ds = self.ds
        if param not in ds:
            raise ValueError(f"Parameter {param} not in dataset")

        # First set some plot parameters:
        minLon, minLat, maxLon, maxLat = (
            ds[self.lonname].values[0],
            ds[self.latname].values[0],
            ds[self.lonname].values[-1],
            ds[self.latname].values[-1],
        )
        extents = [minLon, maxLon, minLat, maxLat]

        # create figure and plot/map
        fig, ax = plt.subplots(
            1,
            1,
            figsize=(fscale, fscale * (maxLat - minLat) / (maxLon - minLon)),
            subplot_kw={"projection": ccrs.PlateCarree()},
        )
        # ax.set_extent(extents, crs=ccrs.PlateCarree())

        coastline = cfeature.GSHHSFeature(
            scale="auto", edgecolor="black", facecolor=cfeature.COLORS["land"]
        )

        ds[param].isel(isel).plot(ax=ax, cmap=cmap, **kwargs)

        ax.add_feature(coastline)
        ax.add_feature(cfeature.BORDERS, linewidth=2)

        gl = ax.gridlines(
            crs=ccrs.PlateCarree(),
            draw_labels=True,
            linewidth=2,
            color="gray",
            alpha=0.5,
            linestyle="--",
        )

        gl.xformatter = LONGITUDE_FORMATTER
        gl.yformatter = LATITUDE_FORMATTER

        # Plot the model domain
        if model_grid:
            bx, by = model_grid.boundary_points()
            poly = plt.Polygon(list(zip(bx, by)), facecolor="r", alpha=0.05)
            ax.add_patch(poly)
            ax.plot(bx, by, lw=2, color="k")
        return fig, ax

    def get(self, stage_dir: str) -> "DataGrid":
        """Write the data source to a new location"""
        dest = os.path.join(stage_dir, f"{self.id}.nc")
        self.ds.to_netcdf(dest, **self.netcdf_kwargs)
        return DataGrid(id=self.id, path=dest)
