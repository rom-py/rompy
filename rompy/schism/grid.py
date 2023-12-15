import logging
from pathlib import Path
from typing import Literal, Optional

import numpy as np
import pandas as pd
from pydantic import Field, field_validator, model_validator
from pyschism.mesh import Hgrid
from pyschism.mesh.prop import Tvdflag
from pyschism.mesh.vgrid import Vgrid
from shapely.geometry import MultiPoint, Polygon

from rompy.core import DataBlob, RompyBaseModel
from rompy.core.grid import BaseGrid

logger = logging.getLogger(__name__)


import os

from pydantic import BaseModel, field_validator


class GR3Generator(RompyBaseModel):
    hgrid: DataBlob | Path = Field(..., description="Path to hgrid.gr3 file")
    gr3_type: str = Field(
        ...,
        description="Type of gr3 file. Must be one of 'albedo', 'diffmin', 'diffmax', 'watertype', 'windrot_geo2proj'",
    )
    val: float = Field(None, description="Constant value to set in gr3 file")

    @field_validator("gr3_type")
    def gr3_type_validator(cls, v):
        if v not in [
            "albedo",
            "diffmin",
            "diffmax",
            "watertype",
            "windrot_geo2proj",
        ]:
            raise ValueError(
                "gr3_type must be one of 'albedo', 'diffmin', 'diffmax', 'watertype', 'windrot_geo2proj'"
            )
        return v

    @property
    def id(self):
        return self.gr3_type

    def generate_gr3(self, destdir: str | Path) -> Path:
        if isinstance(self.hgrid, DataBlob):
            if not self.hgrid._copied:
                self.hgrid.get(destdir)
            ref = self.hgrid._copied
        else:
            ref = self.hgrid
        dest = Path(destdir) / f"{self.gr3_type}.gr3"
        with open(ref, "r") as inFile:
            with open(dest, "w") as outFile:
                # blank line
                line = inFile.readline()
                outFile.write(f"{self.val}\n")

                # ne, np
                line = inFile.readline()
                outFile.write(line)

                ne, np1 = map(int, line.strip().split())

                for i in range(np1):
                    line = inFile.readline().strip()
                    id, x, y, z = map(float, line.split())
                    outFile.write(f"{id} {x} {y} {self.val}\n")

                for i in range(ne):
                    line = inFile.readline()
                    outFile.write(line)
                return dest

    def get(self, destdir: str | Path) -> Path:
        """Alias to maintain api compatibility with DataBlob"""
        return self.generate_gr3(destdir)


# TODO - check datatypes for gr3 files (int vs float)
class SCHISMGrid2D(BaseGrid):
    """2D SCHISM grid in geographic space."""

    grid_type: Literal["2D", "3D"] = Field(
        "2D", description="Type of grid (2D=two dimensional, 3D=three dimensional)"
    )
    hgrid: DataBlob = Field(..., description="Path to hgrid.gr3 file")
    drag: Optional[DataBlob] = Field(default=None, description="Path to drag.gr3 file")
    rough: Optional[DataBlob] = Field(
        default=None, description="Path to rough.gr3 file"
    )
    manning: Optional[DataBlob | float] = Field(
        default=None, description="Path to manning.gr3 file"
    )
    hgridll: Optional[DataBlob | int] = Field(
        default=None, description="Path to hgrid.ll file. "
    )
    diffmin: Optional[DataBlob | float] = Field(
        default=1.0e-6,
        description="Path to diffmax.gr3 file or constant value",
        validate_default=True,
    )
    diffmax: Optional[DataBlob | float] = Field(
        default=1.0,
        description="Path to diffmax.gr3 file or constant value",
        validate_default=True,
    )
    albedo: Optional[DataBlob | float] = Field(
        default=0.15,
        description="Path to albedo.gr3 file or constant value",
        validate_default=True,
    )
    watertype: Optional[DataBlob | int] = Field(
        default=1,
        description="Path to watertype.gr3 file or constant value",
        validate_default=True,
    )
    windrot_geo2proj: Optional[DataBlob | float] = Field(
        default=0.0,
        description="Path to windrot_geo2proj.gr3 file or constant value",
        validate_default=True,
    )
    hgrid_WWM: Optional[DataBlob | int] = Field(
        default=None, description="Path to hgrid_WWM.gr3 file"
    )
    wwmbnd: Optional[DataBlob | int] = Field(
        default=None, description="Path to wwmbnd.gr3 file"
    )
    _pyschism_hgrid: Optional[Hgrid] = None
    _pyschism_vgrid: Optional[Vgrid] = None

    @model_validator(mode="after")
    def validate_rough_drag_manning(cls, v):
        if sum([v.rough is not None, v.drag is not None, v.manning is not None]) > 1:
            raise ValueError("Only one of rough, drag, manning can be set")
        return v

    # validator that checks for gr3 source and if if not a daba blob or GR3Input, initializes a GR3Generator
    @field_validator(
        "drag",
        "rough",
        "manning",
        "hgridll",
        "diffmin",
        "diffmax",
        "albedo",
        "watertype",
        "windrot_geo2proj",
        "hgrid_WWM",
        "wwmbnd",
        mode="after",
    )
    def gr3_source_validator(cls, v, values):
        if v is not None:
            if not isinstance(v, DataBlob):
                v = GR3Generator(
                    hgrid=values.data["hgrid"], gr3_type=values.field_name, val=v
                )
        return v

    @model_validator(mode="after")
    def set_xy(cls, v):
        if v.hgrid is not None:
            v._pyschism_hgrid = Hgrid.open(v.hgrid._copied or v.hgrid.source)
            v.x = v._pyschism_hgrid.x
            v.y = v._pyschism_hgrid.y
        return v

    @property
    def pyschism_hgrid(self):
        if self._pyschism_hgrid is None:
            self._pyschism_hgrid = Hgrid.open(self.hgrid._copied or self.hgrid.source)
        return self._pyschism_hgrid

    @property
    def pyschism_vgrid(self):
        if self._pyschism_vgrid is None:
            self._pyschism_vgrid = Vgrid.open(self.vgrid._copied or self.vgrid.source)
        return self._pyschism_vgrid

    def get(self, destdir: Path) -> dict:
        ret = {}
        for filetype in [
            "hgrid",
            "drag",
            "rough",
            "manning",
            "diffmin",
            "diffmax",
            "hgridll",
            "hgrid_WWM",
            "wwmbnd",
            "albedo",
            "watertype",
            "windrot_geo2proj",
        ]:
            source = getattr(self, filetype)
            if filetype == "hgridll":
                if source is None:
                    logger.info(f"Creating symbolic link for hgrid.ll")
                    os.symlink("./hgrid.gr3", f"{destdir}/hgrid.ll")
                    continue
            if source is not None:
                source.get(destdir)
        self.generate_tvprop(destdir)
        return ret

    def generate_tvprop(self, destdir: Path) -> Path:
        """Generate tvprop.in file

        Args:
            destdir (Path): Destination directory

        Returns:
            Path: Path to tvprop.in file
        """
        # TODO - should this be handled in the same way as the gr3 files? i.e. would you
        # ever want to provide a file path to tvprop.in?
        tvdflag = Tvdflag(
            self.pyschism_hgrid, np.array([1] * len(self.pyschism_hgrid.elements))
        )
        tvdflag.write(destdir / "tvprop.in")
        return destdir / "tvprop.in"

    def _get_boundary(self, tolerance=None) -> Polygon:
        bnd = pd.concat(
            [
                self.pyschism_hgrid.hgrid.boundaries.open.get_coordinates(),
                self.pyschism_hgrid.hgrid.boundaries.land.get_coordinates(),
            ]
        )
        # convert pandas dataframe to polygon
        polygon = Polygon(zip(bnd.x.values, bnd.y.values))
        if tolerance:
            polygon = polygon.simplify(tolerance=tolerance)
        return polygon

    def plot_hgrid(self):
        import matplotlib.pyplot as plt
        from cartopy import crs as ccrs
        from matplotlib.tri import Triangulation

        fig = plt.figure(figsize=(20, 10))
        ax = fig.add_subplot(121)
        ax.set_title("Bathymetry")

        hgrid = Hgrid.open(self.hgrid._copied or self.hgrid.source)
        self.pyschism_hgrid.make_plot(axes=ax)

        # open boundary nodes/info as geopandas df
        gdf_open_boundary = hgrid.boundaries.open

        # make a pandas dataframe for easier lon/lat referencing during forcing condition generation
        df_open_boundary = pd.DataFrame(
            {
                "schism_index": gdf_open_boundary.index_id[0],
                "index": gdf_open_boundary.indexes[0],
                "lon": gdf_open_boundary.get_coordinates().x,
                "lat": gdf_open_boundary.get_coordinates().y,
            }
        ).reset_index(drop=True)

        # create sub-sampled wave boundary
        # #wave_boundary = redistribute_vertices(gdf_open_boundary.geometry[0], 0.2)
        #
        # df_wave_boundary = pd.DataFrame(
        #     {"lon": wave_boundary.xy[0], "lat": wave_boundary.xy[1]}
        # ).reset_index(drop=True)

        meshtri = Triangulation(
            self.pyschism_hgrid.x,
            self.pyschism_hgrid.y,
            self.pyschism_hgrid.elements.array,
        )
        ax = fig.add_subplot(122, projection=ccrs.PlateCarree())
        ax.triplot(meshtri, color="k", alpha=0.3)
        gdf_open_boundary.plot(ax=ax, color="b")
        ax.add_geometries(
            self.pyschism_hgrid.boundaries.land.geometry.values,
            facecolor="none",
            edgecolor="g",
            linewidth=2,
            crs=ccrs.PlateCarree(),
        )
        ax.plot(
            df_open_boundary["lon"],
            df_open_boundary["lat"],
            "+k",
            transform=ccrs.PlateCarree(),
            zorder=10,
        )
        ax.plot(
            df_open_boundary["lon"],
            df_open_boundary["lat"],
            "xr",
            transform=ccrs.PlateCarree(),
            zorder=10,
        )
        # ax.plot(
        #     df_wave_boundary["lon"],
        #     df_wave_boundary["lat"],
        #     "+k",
        #     transform=ccrs.PlateCarree(),
        #     zorder=10,
        # )
        # ax.plot(
        #     df_wave_boundary["lon"],
        #     df_wave_boundary["lat"],
        #     "xr",
        #     transform=ccrs.PlateCarree(),
        #     zorder=10,
        # )
        ax.coastlines()
        ax.set_title("Mesh")

    def ocean_boundary(self):
        bnd = self.pyschism_hgrid.boundaries.open.get_coordinates()
        return bnd.x.values, bnd.y.values

    def land_boundary(self):
        bnd = self.pyschism_hgrid.boundaries.land.get_coordinates()
        return bnd.x.values, bnd.y.values


class SCHISMGrid3D(SCHISMGrid2D):
    """3D SCHISM grid in geographic space."""

    grid_type: Literal["2D", "3D"] = Field(
        "3D", description="Type of grid (2D=two dimensional, 3D=three dimensional)"
    )
    vgrid: DataBlob = Field(..., description="Path to vgrid.in file")

    def get(self, destdir: Path):
        ret = super().get(destdir)
        for filetype in [
            "vgrid",
        ]:
            source = getattr(self, filetype)
            if source is not None:
                logger.info(
                    f"Copying {source.id}: {source.source} to {destdir}/{source.source}"
                )
                source.get(destdir)
        return ret


if __name__ == "__main__":
    import cartopy.crs as ccrs
    import matplotlib.pyplot as plt

    grid = SCHISMGrid2D(
        hgrid=DataBlob(
            source="../../tests/schism/test_data/hgrid.gr3",
            id="hgrid",
        )
    )
    grid.plot_hgrid()
    # plt.figure()
    # grid._set_xy()
    # bnd = grid.boundary()
    # ax = plt.axes(projection=ccrs.PlateCarree())
    # # plot polygon on cartopy axes
    # ax.add_geometries([bnd], ccrs.PlateCarree(), facecolor="none", edgecolor="red")
    # ax.coastlines()
    plt.show()