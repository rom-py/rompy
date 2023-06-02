import logging
from typing import Optional

import numpy as np
from pydantic import Field, root_validator
from pydantic_numpy import NDArray
from shapely.geometry import Polygon
from typing_extensions import Literal

from .types import Bbox, RompyBaseModel

# pydantic interface to BaseNumericalModel
# https://pydantic-docs.helpmanual.io/usage/models/

# comment using numpy style docstrings

logger = logging.getLogger(__name__)


class BaseGrid(RompyBaseModel):
    """
    An object which provides an abstract representation of a grid in some geographic space

    This is the base class for all Grid objects. The minimum representation of a grid are two
    NumPy array's representing the vertices or nodes of some structured or unstructured grid,
    its bounding box and a boundary polygon. No knowledge of the grid connectivity is expected.
    """

    x: Optional[NDArray] = Field(description="A 1D array of x coordinates")
    y: Optional[NDArray] = Field(description="A 1D array of y coordinates")
    grid_type: Literal["base"] = "base"

    @property
    def minx(self) -> float:
        return np.nanmin(self.x)

    @property
    def maxx(self) -> float:
        return np.nanmax(self.x)

    @property
    def miny(self) -> float:
        return np.nanmin(self.y)

    @property
    def maxy(self) -> float:
        return np.nanmax(self.y)

    def bbox(self, buffer=0.0) -> Bbox:
        """Returns a bounding box for the spatial grid

        This function returns a list [ll_x, ll_y, ur_x, ur_y]
        where ll_x, ll_y (ur_x, ur_y) are the lower left (upper right)
        x and y coordinates bounding box of the model domain

        """
        ll_x = self.minx - buffer
        ll_y = self.miny - buffer
        ur_x = self.maxx + buffer
        ur_y = self.maxy + buffer
        bbox = [ll_x, ll_y, ur_x, ur_y]
        return bbox

    def _get_boundary(self, tolerance=0.2) -> Polygon:
        from shapely.geometry import MultiPoint

        xys = list(zip(self.x.flatten(), self.y.flatten()))
        polygon = MultiPoint(xys).convex_hull
        polygon = polygon.simplify(tolerance=tolerance)

        return polygon

    def boundary(self, tolerance=0.2):
        """
        Returns a boundary polygon as a Shapely Polygon object. Sub-classes can override the private method Grid._get_boundary() but must return a Shapely polygon object.

        Parameters
        ----------
        tolerance : float
            See https://shapely.readthedocs.io/en/stable/manual.html#object.simplify

        Returns
        -------
        polygon : shapely.Polygon see https://shapely.readthedocs.io/en/stable/manual.html#Polygon

        """
        return self._get_boundary(tolerance=tolerance)

    def boundary_points(self, tolerance=0.2):
        """
        Convenience function to convert boundary Shapely Polygon
        to arrays of coordinates

        Parameters
        ----------
        tolerance : float
            Passed to Grid.boundary
            See https://shapely.readthedocs.io/en/stable/manual.html#object.simplify

        """
        polygon = self.boundary(tolerance=tolerance)
        hull_x, hull_y = polygon.exterior.coords.xy
        return hull_x, hull_y

    def plot(self, fscale=10):
        """Plot the grid"""

        import cartopy.crs as ccrs
        import cartopy.feature as cfeature
        import matplotlib.pyplot as plt
        from cartopy.mpl.gridliner import LATITUDE_FORMATTER, LONGITUDE_FORMATTER

        # First set some plot parameters:
        bbox = self.bbox(buffer=0.1)
        minLon, minLat, maxLon, maxLat = bbox
        extents = [minLon, maxLon, minLat, maxLat]

        # create figure and plot/map
        fig, ax = plt.subplots(
            1,
            1,
            figsize=(fscale, fscale * (maxLon - minLon) / (maxLat - minLat)),
            subplot_kw={"projection": ccrs.PlateCarree()},
        )
        ax.set_extent(extents, crs=ccrs.PlateCarree())

        coastline = cfeature.GSHHSFeature(
            scale="auto", edgecolor="black", facecolor=cfeature.COLORS["land"]
        )
        ax.add_feature(coastline, zorder=0)
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
        bx, by = self.boundary_points()
        poly = plt.Polygon(list(zip(bx, by)), facecolor="r", alpha=0.05)
        ax.add_patch(poly)
        ax.plot(bx, by, lw=2, color="k")
        return fig, ax

    def __repr__(self):
        return f"{self.__class__.__name__}({self.x}, {self.y})"

    def __eq__(self, other):
        return self.dict() == other.dict()


class RegularGrid(BaseGrid):
    grid_type: Literal["regular"] = "regular"
    x0: Optional[float] = None
    y0: Optional[float] = None
    rot: Optional[float] = 0.0
    dx: Optional[float] = None
    dy: Optional[float] = None
    nx: Optional[int] = None
    ny: Optional[int] = None
    _x0: Optional[float]
    _y0: Optional[float]
    _rot: Optional[float]
    _dx: Optional[float]
    _dy: Optional[float]
    _nx: Optional[int]
    _ny: Optional[int]

    @root_validator
    def validate_grid(cls, values):
        x = values["x"]
        y = values["y"]
        x0 = values["x0"]
        y0 = values["y0"]
        dx = values["dx"]
        dy = values["dy"]
        nx = values["nx"]
        ny = values["ny"]

        if isinstance(x, np.ndarray) or isinstance(y, np.ndarray):
            if any([x0, y0, dx, dy, nx, ny]):
                raise ValueError(
                    "x, y provided explicitly, cant process x0, y0, dx, dy, nx, ny"
                )
            return values
        for var in [x0, y0, dx, dy, nx, ny]:
            if var is None:
                raise ValueError("x0, y0, dx, dy, nx, ny must be provided for REG grid")
        return values

    def __init__(self, **data):
        super().__init__(**data)
        if not isinstance(self.x, np.ndarray) or not isinstance(self.y, np.ndarray):
            self._x0 = self.x0
            self._y0 = self.y0
            self._rot = self.rot
            self._dx = self.dx
            self._dy = self.dy
            self._nx = self.nx
            self._ny = self.ny
            self._regen_grid()

    def _regen_grid(self):
        _x, _y = self._gen_reg_cgrid()
        self.x = _x
        self.y = _y

    def _gen_reg_cgrid(self):
        # Grid at origin
        i = np.arange(0.0, self.dx * self.nx, self.dx)
        j = np.arange(0.0, self.dy * self.ny, self.dy)
        ii, jj = np.meshgrid(i, j)

        # Rotation
        alpha = -self.rot * np.pi / 180.0
        R = np.array([[np.cos(alpha), -np.sin(alpha)], [np.sin(alpha), np.cos(alpha)]])
        gg = np.dot(np.vstack([ii.ravel(), jj.ravel()]).T, R)

        # Translation
        x = gg[:, 0] + self.x0
        y = gg[:, 1] + self.y0

        x = np.reshape(x, ii.shape)
        y = np.reshape(y, ii.shape)
        return x, y

    def __repr__(self):
        return f"{self.__class__.__name__}({self.nx}, {self.ny})"

    def __str__(self):
        return f"{self.__class__.__name__}({self.nx}, {self.ny})"


if __name__ == "__main__":
    import matplotlib.pyplot as plt

    # model = BaseModel()
    x = np.array([0, 1, 2, 3])
    y = np.array([0, 1, 2, 3])
    xx, yy = np.meshgrid(x, y)
    grid = BaseGrid(x=xx, y=yy)
    grid.plot()
    plt.show()
