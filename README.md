---
title: "Relocatable Ocean Modelling in PYthon (rompy)"
---

[![PyPI version](https://badge.fury.io/py/rompy.svg)](https://badge.fury.io/py/rompy)
[![Documentation Status](https://github.com/rom-py/rompy/actions/workflows/sphinx_docs_to_gh_pages.yaml/badge.svg)](https://rom-py.github.io/rompy/)

# Introduction

Relocatable Ocean Modelling in PYthon (rompy) combines templated cookie-cutter model configuration with various `xarray` extensions to assist in the setup and evaluation of coastal ocean models, and is intended to simplify their configuration, execution and analysis. This repository also includes [Jupyter notebooks](./notebooks) that provide examples to illustrate the use of `rompy` code, create visualisations and provide inline documentation. Currently `rompy` implements one model class for the [SWAN wave model](https://swanmodel.sourceforge.io/) developed by Delft University of Technology.

# Jupyter Notebooks

Jupyter notebooks in the [`./notebooks`](./notebooks) directory include:

+ [catalog_advanced_BOM_WW3.ipynb](./notebooks/catalog_advanced_BOM_WW3.ipynb)

    Opens the included `rompy` catalog and demonstrates reading BoM WaveWatch III data. A visualisation example uses `geoviews` to show the location of the WaveWatch III data overlayed on satellite imagery. This notebook also shows how a filter can be used with the catalog to load only a specific wave station.

+ [catalog_basic_AODN.ipynb](./notebooks/catalog_basic_AODN.ipynb)

    Opens the included `rompy` catalog and demonstrates reading the remotely sensed near-real-time SAR dataset from the AODN. It also demonstrates plotting the SAR locations and image timing via `rompy` visualisation and shows the data as a timeseries using `xarray` plotting.

+ [catalog_basic_CSIRO_SWAN.ipynb](./notebooks/catalog_basic_CSIRO_SWAN.ipynb)

    Opens the included `rompy` catalog and demonstrates reading and visualising the SWAN model outputs stored remotely on CSIRO thredds servers. This notebook provides visualisation of wave height as a spatial surface at a particular time with the `holoviews` package, and as a time series at a particular point. It shows a contour visualisation of spectral characteristics and waves at a point in space and time using the `wavespectra` package.
    
+ [model_swan_example.ipynb](./notebooks/model_swan_example.ipynb)

    Shows how the SwanModel class can be used to generate configuration for a SWAN model. It shows the creation of a SwanModel instance from a template and demonstrates the visualisation of the spatial boundaries of the SwanModel derived from the template.
    
+ [rompy-dev_matchup_code.ipynb](./notebooks/rompy-dev_matchup_code.ipynb)

    Development and testing of a function to match SwanModel outputs with observed data collected from a waverider buoy.
    
# Intake catalogs

YAML files in the [`./rompy/catalogs`](./rompy/catalogs) directory are automatically parsed into a catalog in the `rompy.cat` variable when `rompy` is imported. The master catalog (`master.yaml`) points at the AODN, WA Department of Transport, CSIRO, and BoM datasets via subcatalogs. 

## CSIRO

The CSIRO catalog provides access to SWAN data runs for Mandurah and Perth domains, the main catalog links to `csiro.yaml` to a catalog hosted on a CSIRO Thredds server. 

## AODN

The AODN catalog provides access to wave buoy, altimetry and remotely sensed SAR wave data. 

## BoM

The BoM catalog provides access to WaveWatch III (wind and waves) forecast data. 

## WA Deptartment of Transport

The WA Deptartment of Transport catalog provides access to raster bathymetry data.

# Intake Drivers

Custom intake drivers are in [`./rompy/intake.py`](./rompy/intake.py). An intake driver is code for loading data in an intake catalog. For example, built-in intake drivers can be associated with NetCDF, CSV, zarr, and other datasets in `intake.yaml`. 

# Model Wrappers

## BaseModel

BaseModel is a general-purpose abstract model wrapper class. BaseModel provides a settings dictionary which is a general-purpose key value store that is used to replace values in the corresponding cookiecutter template.

## SwanModel

SwanModel is a subclass of BaseModel and is a wrapper around a configuration of a SWAN model. SWAN model configurations are a set of files and directories expected by the externally developed SWAN model for it to correctly run and produce output. Therefore, SwanModel provides an interface between python code and the bespoke SWAN model configuration.

## BaseGrid

BaseGrid stores information about a geographic grid. The grid may be structured or unstructured. A list of $x$ and $y$ values can be set to define the grid points. From $x$ and $y$ values a bounding box can be accessed through the `bbox` function and a `shapely` boundary shape generated through the `boundary` function. The `boundary_points` function provides a list of boundary points as coordinates and a `plot` function uses `matplotlib` to plot the grid boundary over a coastline.

## SwanGrid

SwanGrid extends BaseGrid and can be parameterized to provide specific grid types for SWAN. A helper function `nearby_spectra` accepts a spectral file in `wavespectra` `xarray` format and selects spectral points close to the grid boundary.