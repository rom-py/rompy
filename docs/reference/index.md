# API reference

The reference is generated from the rompy source code. Pydantic models list all their fields, including those they inherit.

Model plugins build on these classes. Their own references, for example [rompy-xbeach](https://rom-py.github.io/rompy-xbeach/), show the fields each model class inherits from rompy and link back here.

| Page | Module | Main objects |
|---|---|---|
| [Model run](model.md) | `rompy.model` | `ModelRun` |
| [Model configuration](config.md) | `rompy.core.config` | `BaseConfig` |
| [Time](time.md) | `rompy.core.time` | `TimeRange` |
| [Grids](grid.md) | `rompy.core.grid` | `BaseGrid`, `RegularGrid` |
| [Data](data.md) | `rompy.core.data` | `DataBlob`, `DataPoint`, `DataGrid` |
| [Boundaries](boundary.md) | `rompy.core.boundary` | `DataBoundary`, `BoundaryWaveStation` |
| [Sources](source.md) | `rompy.core.source` | `SourceFile`, `SourceIntake`, `SourceDatamesh`, `SourceWavespectra`, `SourceTimeseriesCSV` |
| [Filters](filters.md) | `rompy.core.filters` | `Filter` |
| [Spectra](spectrum.md) | `rompy.core.spectrum` | `Frequency`, `LogFrequency` |
| [Base types](types.md) | `rompy.core.types` | `RompyBaseModel`, `DatasetCoords`, `Bbox` |
| [Templates and rendering](templates.md) | `rompy.core.render`, `rompy.templating` | `render`, `${VAR}` substitution |
| [YAML loading](yaml.md) | `rompy.core.yaml_loader` | `!include` |
| [Run backends](backends.md) | `rompy.backends`, `rompy.run` | `LocalConfig`, `DockerConfig`, `SlurmConfig` |
| [Postprocessors](postprocess.md) | `rompy.postprocess` | `NoopPostprocessorConfig` |
| [Pipelines](pipeline.md) | `rompy.pipeline` | `LocalPipelineBackend` |
| [Transfers](transfer.md) | `rompy.transfer` | `TransferManager`, transfer backends |
| [Logging and formatting](logging.md) | `rompy.logging`, `rompy.formatting` | logging configuration |

The command line is described in [The command line](../how-to/cli.md).
