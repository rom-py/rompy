"""Rompy core data objects."""

import logging
import os
from abc import ABC, abstractmethod
from pathlib import Path
from shutil import copytree
from typing import Literal, Optional, Union

import cartopy.crs as ccrs
import cartopy.feature as cfeature
import matplotlib.pyplot as plt
from cloudpathlib import AnyPath
from pydantic import Field, PrivateAttr, field_validator, model_validator

from rompy.core.filters import Filter
from rompy.core.grid import BaseGrid, RegularGrid
from rompy.core.time import TimeRange
from rompy.core.types import DatasetCoords, RompyBaseModel, Slice
from rompy.transfer import get_transfer
from rompy.utils import load_entry_points

logger = logging.getLogger(__name__)


class DataBase(ABC, RompyBaseModel):
    """Base class for data objects."""

    model_type: Literal["base"] = Field(
        default="base",
        description="Model type discriminator",
    )
    id: str = Field(
        default="data", description="Unique identifier for this data source"
    )

    @abstractmethod
    def get(self, destdir: Union[str, Path], *args, **kwargs) -> Path:
        """Abstract method to get the data."""
        pass


class DataBlob(DataBase):
    """Data source for model ingestion.

    Generic data source for files that either need to be copied to the model directory
    or linked if `link` is set to True. Supports local/cloud paths, remote HTTP/HTTPS URLs,
    and oceanum:// storage URIs via the transfer registry.

    Parameters
    ----------
    source : str | Path | AnyPath
        URI of the data source: local file path, cloud storage URI (s3://, gs://),
        remote HTTP/HTTPS URL, or oceanum:// storage URI.
    link : bool
        Whether to create a symbolic link instead of copying the file.
        Note: Only works with local file paths (file:// scheme).

    Examples
    --------
    >>> from rompy.core.data import DataBlob
    >>> from pathlib import Path

    Local file:

    >>> blob = DataBlob(source=Path("/data/input.nc"))
    >>> blob.get(Path("/output/dir"))  # doctest: +ELLIPSIS
    PosixPath('/output/dir/input.nc')

    Remote HTTP file (automatically downloaded):

    >>> blob = DataBlob(source="https://example.com/data.nc")
    >>> blob.get(Path("/output/dir"))  # doctest: +ELLIPSIS
    PosixPath('/output/dir/data.nc')

    Remote file with custom name:

    >>> blob = DataBlob(source="https://example.com/data.nc")
    >>> blob.get(Path("/output/dir"), name="custom.nc")  # doctest: +ELLIPSIS
    PosixPath('/output/dir/custom.nc')

    """

    model_type: Literal["data_blob", "data_link"] = Field(
        default="data_blob",
        description="Model type discriminator",
    )
    source: Union[str, Path, AnyPath] = Field(
        description=(
            "URI of the data source: local file path, cloud storage URI (s3://, gs://), "
            "remote HTTP/HTTPS URL, or oceanum:// URL. Sources are handled via the transfer registry."
        ),
    )
    link: bool = Field(
        default=False,
        description="Whether to create a symbolic link instead of copying the file",
    )
    _copied: Optional[str] = PrivateAttr(default=None)

    @model_validator(mode="after")
    def validate_link_scheme_compat(self):
        """Validate that link=True only works with file:// scheme."""
        if self.link:
            from rompy.transfer import parse_scheme

            scheme = parse_scheme(str(self.source))
            if scheme != "file":
                raise ValueError(
                    f"Cannot use link=True with {scheme}:// URIs. "
                    f"Only local file paths support symbolic links."
                )
        return self

    def get(
        self, destdir: Union[str, Path], name: Optional[str] = None, *args, **kwargs
    ) -> Path:
        """Copy, download, or link the data source to a new directory.

        Uses the transfer registry to dispatch based on URI scheme (file://, http://, https://, oceanum://).
        For local files, respects the `link` attribute (symlink vs copy).
        For remote sources (HTTP, oceanum), always downloads (ignores link flag).

        Parameters
        ----------
        destdir : str | Path
            The destination directory to copy/download/link the data source to.
        name : str, optional
            Override the output filename.

        Returns
        -------
        Path
            The path to the downloaded/copied file or created symlink.

        Notes
        -----
        HTTP downloads include:
        - Retry logic with exponential backoff (3 retries by default)
        - Atomic writes (download to temp file, then rename)
        - Caching (skip download if file already exists in destination)
        - 500MB maximum file size limit

        Raises
        ------
        ValueError
            If link=True is used with a non-file:// URI.
        UnsupportedOperation
            If the transfer scheme does not support required operations.
        """
        destdir = Path(destdir).resolve()

        transfer = get_transfer(self.source)
        outfile = transfer.get(
            uri=str(self.source), destdir=destdir, name=name, link=self.link
        )

        self._copied = str(outfile)
        return outfile


GRID_TYPES = Union[BaseGrid, RegularGrid]

# Plugin for the source types
SOURCE_TYPES = load_entry_points("rompy.source")
SOURCE_TYPES_TS = load_entry_points("rompy.source", etype="timeseries")


class DataPoint(DataBase):
    """Data object for timeseries source data.

    Generic data object for xarray datasets that only have time as a dimension and do
    not need to be cropped to a specific grid.

    """

    model_type: Literal["point"] = Field(
        default="point",
        description="Model type discriminator",
    )
    source: Union[SOURCE_TYPES_TS] = Field(
        description=(
            "Source reader, must return an xarray timeseries point dataset "
            "in the open method"
        ),
        discriminator="model_type",
    )
    filter: Optional[Filter] = Field(
        default_factory=Filter,
        description="Optional filter specification to apply to the dataset",
    )
    variables: Optional[list[str]] = Field(
        [], description="Subset of variables to extract from the dataset"
    )
    coords: Optional[DatasetCoords] = Field(
        default=DatasetCoords(),
        description="Names of the coordinates in the dataset",
    )
    crop_data: bool = Field(
        default=True,
        description=(
            "Update crop filters from Grid and Time objects if passed to get method"
        ),
    )
    buffer: float = Field(
        default=0.0,
        description="Space to buffer the grid bounding box if `filter_grid` is True",
    )
    time_buffer: list[int] = Field(
        default=[0, 0],
        description=(
            "Number of source data timesteps to buffer the time range "
            "if `filter_time` is True"
        ),
    )

    def _filter_grid(self, grid: GRID_TYPES):
        """No spatial selection is required for timeseries data."""
        pass

    def _filter_time(self, time: TimeRange, end_buffer=1):
        """Define the filters to use to extract data to this grid"""
        start = time.start
        end = time.end
        t = self.coords.t
        if t in self.source.coordinates and self.source.coordinates[t].size > 1:
            times = self.source.coordinates[t].to_index().to_pydatetime()
            dt = times[1] - times[0]
            if self.time_buffer[0]:
                start -= dt * self.time_buffer[0]
            if self.time_buffer[1]:
                end += dt * self.time_buffer[1]
        self.filter.crop.update({t: Slice(start=start, stop=end)})

    @property
    def ds(self):
        """Return the xarray dataset for this data source."""
        ds = self.source.open(
            variables=self.variables, filters=self.filter, coords=self.coords
        )
        return ds

    @property
    def outfile(self) -> str:
        return f"{self.id}.nc"

    def get(
        self,
        destdir: str | Path,
        grid: Optional[GRID_TYPES] = None,
        time: Optional[TimeRange] = None,
    ) -> Path:
        """Write the data source to a new location.

        Parameters
        ----------
        destdir : str | Path
            The destination directory to write the netcdf data to.
        grid: GRID_TYPES, optional
            The grid to filter the data to, only used if `self.crop_data` is True.
        time: TimeRange, optional
            The times to filter the data to, only used if `self.crop_data` is True.

        Returns
        -------
        outfile: Path
            The path to the written file.

        """
        if self.crop_data:
            if grid is not None:
                self._filter_grid(grid)
            if time is not None:
                self._filter_time(time)
        outfile = Path(destdir) / self.outfile
        self.ds.to_netcdf(outfile)
        return outfile


class DataGrid(DataPoint):
    """Data object for gridded source data.

    Generic data object for xarray datasets that with gridded spatial dimensions

    Note
    ----
    The fields `filter_grid` and `filter_time` trigger updates to the crop filter from
    the grid and time range objects passed to the get method. This is useful for data
    sources that are not defined on the same grid as the model grid or the same time
    range as the model run.

    """

    model_type: Literal["grid"] = Field(
        default="grid",
        description="Model type discriminator",
    )
    source: Union[SOURCE_TYPES] = Field(
        description="Source reader, must return an xarray gridded dataset in the open method",
        discriminator="model_type",
    )

    def _filter_grid(self, grid: GRID_TYPES):
        """Define the filters to use to extract data to this grid"""
        x0, y0, x1, y1 = grid.bbox(buffer=self.buffer)
        self.filter.crop.update(
            {
                self.coords.x: Slice(start=x0, stop=x1),
                self.coords.y: Slice(start=y0, stop=y1),
            }
        )

    def _figsize(self, x0, x1, y0, y1, fscale):
        xlen = abs(x1 - x0)
        ylen = abs(y1 - y0)
        if xlen >= ylen:
            figsize = (fscale, (fscale * ylen / xlen or fscale) * 0.8)
        else:
            figsize = ((fscale * xlen / ylen) * 1.2 or fscale, fscale)
        return figsize

    def plot(
        self,
        param,
        isel={},
        model_grid=None,
        cmap="turbo",
        figsize=None,
        fscale=10,
        borders=True,
        land=True,
        coastline=True,
        **kwargs,
    ):
        """Plot the grid."""

        projection = ccrs.PlateCarree()
        transform = ccrs.PlateCarree()

        # Sanity checks
        try:
            ds = self.ds[param].isel(isel)
        except KeyError as err:
            raise ValueError(f"Parameter {param} not in dataset") from err

        if ds[self.coords.x].size <= 1:
            raise ValueError(f"Cannot plot {param} with only one x coordinate\n\n{ds}")
        if ds[self.coords.y].size <= 1:
            raise ValueError(f"Cannot plot {param} with only one y coordinate\n\n{ds}")

        # Set some plot parameters:
        x0 = ds[self.coords.x].values[0]
        y0 = ds[self.coords.y].values[0]
        x1 = ds[self.coords.x].values[-1]
        y1 = ds[self.coords.y].values[-1]

        # create figure and plot/map
        if figsize is None:
            figsize = self._figsize(x0, x1, y0, y1, fscale)
        fig = plt.figure(figsize=figsize)
        ax = fig.add_subplot(111, projection=projection)

        ds.plot.pcolormesh(ax=ax, cmap=cmap, **kwargs)

        if borders:
            ax.add_feature(cfeature.BORDERS)
        if land:
            ax.add_feature(cfeature.LAND, zorder=1)
        if coastline:
            ax.add_feature(cfeature.COASTLINE)

        ax.gridlines(
            crs=transform,
            draw_labels=["left", "bottom"],
            linewidth=1,
            color="gray",
            alpha=0.5,
            linestyle="--",
        )

        # Plot the model domain
        if model_grid:
            bx, by = model_grid.boundary_points()
            poly = plt.Polygon(list(zip(bx, by)), facecolor="r", alpha=0.05)
            ax.add_patch(poly)
            ax.plot(bx, by, lw=2, color="k")
        return fig, ax
