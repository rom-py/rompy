# Grids

A grid says where the model is. rompy's grid classes hold the node coordinates and the few operations that data objects and plugins need from any grid: its extent, its outline and points along that outline. Each model plugin subclasses them for the model's own grid.

```python exec="on" session="grids"
# Hidden setup: quiet logging.
from rompy.logging import config as logging_config

logging_config.update(level="WARNING")
```

## BaseGrid

[`BaseGrid`][rompy.core.grid.BaseGrid] is the interface every grid implements. A subclass provides two arrays of node coordinates, `x` and `y`; `BaseGrid` builds the rest from them:

| Member | Returns |
|---|---|
| `minx`, `maxx`, `miny`, `maxy` | The extent of the nodes |
| `bbox(buffer=0.0)` | `[minx, miny, maxx, maxy]`, widened by `buffer` on each side |
| `boundary(tolerance=0.2)` | The outline of the grid, as a [shapely](https://shapely.readthedocs.io/) polygon (the convex hull of the nodes, simplified by `tolerance`) |
| `boundary_points(spacing=None, tolerance=0.2)` | `x` and `y` arrays of points along the outline, at the polygon vertices or every `spacing` along it |
| `plot()` | A map of the outline, with cartopy |

Nothing in `BaseGrid` depends on how the nodes are connected, so the same interface serves regular grids and unstructured meshes. Data objects use `bbox` to crop their source to the grid and `boundary_points` to select boundary data; see [Data and sources](data.md).

## RegularGrid

[`RegularGrid`][rompy.core.grid.RegularGrid] is a rectangular grid defined by its origin, rotation, spacing and size:

| Field | Meaning |
|---|---|
| `x0`, `y0` | Coordinates of the origin, the first node |
| `rot` | Rotation of the x axis, in degrees counter-clockwise from east (default 0) |
| `dx`, `dy` | Spacing between nodes along the grid's x and y axes |
| `nx`, `ny` | Number of nodes along each axis |

All but `rot` are required. The coordinates are in whatever system you use; `RegularGrid` has no coordinate reference system of its own, though plotting assumes longitudes and latitudes.

```python exec="on" source="above" result="text" session="grids"
from rompy.core.grid import RegularGrid

grid = RegularGrid(x0=114.0, y0=-33.0, dx=0.25, dy=0.25, nx=7, ny=9)
print(grid.grid_type, grid.x.shape)
print("bbox:", [float(v) for v in grid.bbox()])
print("bbox with buffer:", [float(v) for v in grid.bbox(buffer=0.5)])
```

`x` and `y` are 2D arrays of shape `(ny, nx)`. With a rotation, the axes turn counter-clockwise about the origin:

```python exec="on" source="above" result="text" session="grids"
rotated = RegularGrid(x0=0.0, y0=0.0, rot=30.0, dx=100.0, dy=100.0, nx=3, ny=2)
print("x:\n", rotated.x.round(1))
print("y:\n", rotated.y.round(1))
print("length of the axes:", rotated.xlen, rotated.ylen)
```

## Outline and boundary points

The outline of a regular grid is its four corners. `boundary_points` returns them, or points spaced evenly along the outline when `spacing` is given, which is how a boundary data object chooses where to extract boundary conditions:

```python exec="on" source="above" result="text" session="grids"
print(grid.boundary())

xs, ys = grid.boundary_points()
print("corners:", list(zip(xs.tolist(), ys.tolist())))

xs, ys = grid.boundary_points(spacing=0.5)
print(len(xs), "points every 0.5 degrees along the outline")
```

## Plotting

`plot()` draws the outline on a cartopy map, with coastlines, land and borders from Natural Earth (downloaded on first use). It returns the figure and axes, so more can be drawn on them:

```python
fig, ax = grid.plot(buffer=0.5)
```

Pass `ax` to draw on an existing cartopy map, and `land`, `coastline` and `borders` to turn the map features off.

## The grid in YAML

A grid is written as a mapping of its fields. `grid_type` names the kind of grid: `regular` here, `schism` for rompy-schism's mesh. Plugins can use it to accept more than one grid class in a field. The rotated grid above, written out:

```python exec="on" source="above" result="text" session="grids"
import yaml

print(yaml.safe_dump(rotated.model_dump(mode="json"), sort_keys=False))
```

## Grids in the model plugins

Each plugin defines the grid its model needs, based on these classes:

| Plugin | Grid class | Based on | Adds |
|---|---|---|---|
| [rompy-xbeach](https://rom-py.github.io/rompy-xbeach/) | `RegularGrid` | `BaseGrid` | Origin given in any coordinate system, projected `crs`, rotation `alfa`, the XBeach grid parameters |
| [rompy-swan](https://rom-py.github.io/rompy-swan/) | `SwanGrid` | `RegularGrid` | Regular or curvilinear (`grid_type` `REG` or `CURV`), exception value, the `CGRID` and `INPGRID` commands |
| [rompy-schism](https://rom-py.github.io/rompy-schism/) | `SCHISMGrid` | `BaseGrid` | Unstructured horizontal mesh (`hgrid`, a `hgrid.gr3` file) and vertical grid (`vgrid`) |

Because they share `BaseGrid`, rompy's data objects work with any of them. [Your first XBeach model](https://rom-py.github.io/rompy-xbeach/getting-started/first-model/) shows a plugin grid in use.
