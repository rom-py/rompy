# Core Concepts

> [!NOTE]
> For information about Rompy's formatting and logging system, see [formatting_and_logging](formatting_and_logging.md).
> 
> For details on using the command line interface, see [cli](cli.md).

Rompy is a Python library for generating ocean model control files and required input data ready for ingestion into the model. The framework is separated into two broad concepts:

::: rompy.model.ModelRun
::: rompy.core.config.BaseConfig

There is information about each of these in the documentation of each object, but at a high level, ModelRun is the high level framework that renders the config object and controls the period of which the model is run, and the config object is responsible for producing model configuration. 

If we consider a very simple case using the `BaseConfig` class. This is not intended to do anything except provide a base class on which to implement a specific model, however, is is functional and can be used to demonstrate core concepts.

## Core objects 

### Grid

Grids form a core component of any model. Rompy provides a base class for grids, and a regular grid class. Support for other grid types will be added in the future.

::: rompy.core.grid.BaseGrid
::: rompy.core.grid.RegularGrid

### Data

Data objects are used to represent data inputs into the model. Rompy provides the following base classes for data objects:

::: rompy.core.data.DataBlob
::: rompy.core.data.DataGrid
::: rompy.core.source.SourceBase
::: rompy.core.source.SourceFile
::: rompy.core.source.SourceIntake

### Boundary

::: rompy.core.boundary.BoundaryWaveStation
::: rompy.core.source.SourceWavespectra

### Spectrum

::: rompy.core.spectrum.LogFrequency

## Model Run 

::: rompy.model.ModelRun