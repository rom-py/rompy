.. _cli:

Command Line Interface
======================

The ROMPY Command Line Interface (CLI) provides a comprehensive set of tools for generating, running, and processing ocean, wave, and hydrodynamic model configurations with support for multiple execution backends.

Overview
--------

ROMPY CLI has been redesigned with a modern command structure that separates different operations:

.. code-block:: bash

    rompy <command> [options] [arguments]

Available Commands
------------------

.. program:: rompy

run
~~~

Execute a model configuration using a Pydantic backend configuration.

.. code-block:: bash

    rompy run <config-file> --backend-config <backend-config-file> [OPTIONS]

**Options:**

.. option:: --backend-config PATH

    **Required.** YAML/JSON file with backend configuration

.. option:: --dry-run

    Generate inputs only, don't run the model

**Examples:**

.. code-block:: bash

    # Run with local backend configuration
    rompy run model.yml --backend-config local_backend.yml

    # Run with Docker backend configuration
    rompy run model.yml --backend-config docker_backend.yml

    # Dry run (generate only, don't execute)
    rompy run model.yml --backend-config local_backend.yml --dry-run

backends
~~~~~~~~

Manage execution backend configurations.

.. code-block:: bash

    rompy backends <subcommand> [OPTIONS]

**Subcommands:**

list
    List available backends and configuration types

validate
    Validate a backend configuration file

schema
    Generate JSON schema for backend configurations

create
    Create template backend configuration files

**Examples:**

.. code-block:: bash

    # List available backends
    rompy backends list

    # Validate configuration
    rompy backends validate my_config.yml --backend-type local

    # Generate schema
    rompy backends schema --backend-type docker --format json

    # Create template
    rompy backends create --backend-type local --output local_template.yml

Backend Configuration Files
----------------------------

Backend configurations are defined in YAML or JSON files with a ``type`` field indicating the backend type:

**Local Backend Configuration:**

.. code-block:: yaml

    type: local
    timeout: 3600
    env_vars:
      OMP_NUM_THREADS: "4"
      MODEL_DEBUG: "true"
    command: "python run_model.py --verbose"
    shell: true
    capture_output: true

**Docker Backend Configuration:**

.. code-block:: yaml

    type: docker
    image: "swan:latest"
    cpu: 4
    memory: "2g"
    timeout: 7200
    env_vars:
      SWAN_THREADS: "4"
    volumes:
      - "/data/input:/app/input:ro"
      - "/data/output:/app/output:rw"
    executable: "/usr/local/bin/swan"

For complete configuration options, see :doc:`backend_configurations`.

.. code-block:: bash

    rompy run config.yaml --backend docker --timeout 3600 --env OMP_NUM_THREADS=4

pipeline
~~~~~~~~

Run the complete model pipeline: generate → run → postprocess.

.. code-block:: bash

    rompy pipeline <config-file> [OPTIONS]

**Options:**

.. option:: --run-backend TEXT

    Execution backend for run stage (default: local)

.. option:: --processor TEXT

    Postprocessor to use (default: noop)

.. option:: --cleanup-on-failure, --no-cleanup

    Clean up outputs on pipeline failure (default: False)

.. option:: --validate-stages, --no-validate

    Validate each stage before proceeding (default: True)

**Example:**

.. code-block:: bash

    rompy pipeline config.yaml --run-backend docker --processor analysis

generate
~~~~~~~~

Generate model input files without running the model.

.. code-block:: bash

    rompy generate <config-file> [OPTIONS]

**Options:**

.. option:: --output-dir PATH

    Override output directory from configuration

**Example:**

.. code-block:: bash

    rompy generate config.yaml --output-dir ./test_inputs

validate
~~~~~~~~

Validate model configuration without execution.

.. code-block:: bash

    rompy validate <config-file>

**Example:**

.. code-block:: bash

    rompy validate config.yaml

backends
~~~~~~~~

Manage and inspect execution backends.

.. code-block:: bash

    rompy backends list

**Subcommands:**

.. option:: list

    List all available backends (run, postprocess, pipeline)

**Example:**

.. code-block:: bash

    rompy backends list

schema
~~~~~~

Show configuration schema information.

.. code-block:: bash

    rompy schema [OPTIONS]

**Options:**

.. option:: --model-type TEXT

    Show schema for specific model type

**Example:**

.. code-block:: bash

    rompy schema --model-type swan

Global Options
--------------

All commands support these common options:

.. option:: -v, --verbose

    Increase verbosity (can be used multiple times: -v, -vv)

.. option:: --log-dir PATH

    Directory to save log files

.. option:: --show-warnings, --hide-warnings

    Show or hide Python warnings (default: hide)

.. option:: --ascii-only, --unicode

    Use ASCII-only characters in output (default: unicode)

.. option:: --simple-logs, --detailed-logs

    Use simple log format without timestamps and module names (default: detailed)

.. option:: --version

    Show version information and exit

Backend Types
-------------

ROMPY supports multiple execution backends through its plugin architecture:

Run Backends
~~~~~~~~~~~~

Execute models in different environments:

- **local**: Execute directly on the local system
- **docker**: Execute inside Docker containers
- **slurm**: Execute via SLURM job scheduler (if available)
- **kubernetes**: Execute on Kubernetes clusters (if available)

Postprocessors
~~~~~~~~~~~~~~

Handle model output analysis and transformation:

- **noop**: No-operation processor (validation only)
- **analysis**: Statistical analysis and metrics calculation
- **visualization**: Generate plots and animations
- **netcdf**: NetCDF output processing and compression

Pipeline Backends
~~~~~~~~~~~~~~~~~

Orchestrate complete workflows:

- **local**: Execute all stages locally
- **hpc**: HPC-optimized pipeline execution
- **cloud**: Cloud-native pipeline execution

Examples
--------

Basic Model Execution
~~~~~~~~~~~~~~~~~~~~~

Execute a SWAN model with local backend:

.. code-block:: bash

    rompy run swan_config.yaml

Execute with Docker backend and custom settings:

.. code-block:: bash

    rompy run schism_config.yaml \
        --backend docker \
        --timeout 7200 \
        --env OMP_NUM_THREADS=8 \
        --env SCHISM_USE_MPI=true

Complete Pipeline Workflow
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Run complete pipeline with analysis:

.. code-block:: bash

    rompy pipeline ocean_model.yaml \
        --run-backend local \
        --processor analysis \
        --validate-stages

Development Workflow
~~~~~~~~~~~~~~~~~~~~

Validate configuration and generate inputs for testing:

.. code-block:: bash

    # Validate configuration
    rompy validate config.yaml

    # Generate inputs only
    rompy generate config.yaml --output-dir ./test_run

    # Quick test run
    rompy run config.yaml --dry-run --verbose

Production Workflow
~~~~~~~~~~~~~~~~~~~

Full production run with monitoring:

.. code-block:: bash

    rompy pipeline production_config.yaml \
        --run-backend docker \
        --processor full_analysis \
        --log-dir ./logs \
        --verbose \
        --cleanup-on-failure

Configuration Files
-------------------

Enhanced Configuration Structure
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The new CLI supports enhanced configuration files with run and pipeline settings:

.. code-block:: yaml

    # Basic model configuration
    run_id: my_ocean_model
    period:
      start: 20230101T00
      end: 20230102T00
      interval: 3600
    output_dir: ./outputs

    config:
      model_type: schism
      # ... model-specific configuration

    # Run configuration (optional)
    run:
      backend: local
      local:
        env_vars:
          OMP_NUM_THREADS: "4"
        timeout: 3600

    # Pipeline configuration (optional)
    pipeline:
      backend: local
      local:
        run_backend: docker
        processor: analysis
        cleanup_on_failure: false

Legacy Configuration
~~~~~~~~~~~~~~~~~~~~

Simple configurations without run/pipeline sections are still supported:

.. code-block:: yaml

    run_id: simple_model
    period:
      start: 20230101T00
      end: 20230102T00
    config:
      model_type: swan
      # ... model configuration

Environment Variables
---------------------

Set default values using environment variables:

.. code-block:: bash

    export ROMPY_LOG_DIR="./logs"
    export ROMPY_ASCII_ONLY="1"
    export ROMPY_SIMPLE_LOGS="1"

    rompy run config.yaml  # Uses environment settings

Monitoring and Debugging
-------------------------

Verbose Output
~~~~~~~~~~~~~~

Use multiple -v flags for increased verbosity:

.. code-block:: bash

    rompy run config.yaml -v      # INFO level
    rompy run config.yaml -vv     # DEBUG level

Log Files
~~~~~~~~~

Save detailed logs to files:

.. code-block:: bash

    rompy pipeline config.yaml --log-dir ./logs --verbose

Backend Information
~~~~~~~~~~~~~~~~~~~

Inspect available backends:

.. code-block:: bash

    rompy backends list

Validation and Testing
~~~~~~~~~~~~~~~~~~~~~~

Validate configurations before running:

.. code-block:: bash

    rompy validate config.yaml
    rompy generate config.yaml --output-dir ./test

Migration from Legacy CLI
--------------------------

The legacy CLI format is still supported for backward compatibility:

.. code-block:: bash

    # Legacy format (still works)
    rompy swan config.yaml --zip

    # New format (recommended)
    rompy run config.yaml --backend local

However, the new command structure provides more flexibility and features.

Exit Codes
----------

The CLI uses standard exit codes:

- ``0``: Success
- ``1``: Execution error
- ``2``: Configuration or argument error

Troubleshooting
---------------

Common Issues
~~~~~~~~~~~~~

**Configuration Validation Errors:**

.. code-block:: bash

    rompy validate config.yaml

**Backend Not Available:**

.. code-block:: bash

    rompy backends list

**Execution Failures:**

.. code-block:: bash

    rompy run config.yaml --verbose --log-dir ./debug_logs

**Docker Issues:**

.. code-block:: bash

    # Check if Docker backend is available
    rompy backends list | grep docker

    # Test with local backend first
    rompy run config.yaml --backend local

Getting Help
~~~~~~~~~~~~

- Use ``--help`` with any command for detailed options
- Check the developer documentation for architectural details
- Use verbose logging for debugging execution issues
- Validate configurations before running production jobs

.. code-block:: bash

    rompy --help
    rompy run --help
    rompy pipeline --help
