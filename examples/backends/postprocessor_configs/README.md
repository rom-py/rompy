# Postprocessor Configuration Examples

This directory contains example postprocessor configuration files for ROMPY.

## Available Postprocessors

### Noop Postprocessor

The `noop` postprocessor is a placeholder that performs no actual processing but can optionally validate that model outputs exist.

## Files

- **noop_basic.yml** - Minimal configuration with just the required type field
- **noop_advanced.yml** - Shows all available configuration options

## Usage

### Validate a configuration file

```bash
rompy backends validate --processor-type noop noop_basic.yml
```

### Use in postprocessing

```bash
rompy postprocess model_config.yml --processor-config noop_basic.yml
```

### Use in pipeline

```bash
rompy pipeline model_config.yml --processor-config noop_basic.yml
```

## Configuration Schema

All postprocessor configurations share these common fields:

- **type** (required): The postprocessor type (e.g., "noop")
- **timeout** (optional): Maximum execution time in seconds (60-86400, default: 3600)
- **env_vars** (optional): Dictionary of environment variables
- **working_dir** (optional): Working directory for execution

Processor-specific fields vary by type. See individual example files for details.
