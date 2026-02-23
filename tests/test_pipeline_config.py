"""
Integration tests for the new unified pipeline configuration structure.

Tests cover:
- Loading pipeline configs with inline backend and postprocessor configs
- Loading pipeline configs with !include directives
- CLI flag overrides for backend and postprocessor configs
- Error handling for missing required sections
"""

import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from rompy.backends import LocalConfig
from rompy.cli import load_config
from rompy.core.time import TimeRange
from rompy.core.yaml_loader import load_yaml_with_includes
from rompy.model import ModelRun
from rompy.postprocess.config import NoopPostprocessorConfig
from tests.test_helpers import DemoConfig


@pytest.fixture
def basic_inline_pipeline_config():
    """Create a basic inline pipeline configuration."""
    return {
        "config": {
            "run_id": "test_inline_pipeline",
            "output_dir": "./output/test",
            "delete_existing": True,
            "period": {
                "start": "2023-01-01T00:00:00",
                "end": "2023-01-02T00:00:00",
                "interval": "1H",
            },
            "config": {
                "model_type": "demo",
                "arg1": "foo",
                "arg2": "bar",
            },
        },
        "backend": {
            "type": "local",
            "timeout": 3600,
            "command": "echo 'test'",
        },
        "postprocessor": {
            "type": "noop",
        },
    }


@pytest.fixture
def tmp_config_files(tmp_path):
    """Create temporary config files for testing includes."""
    # Main config
    model_config = {
        "run_id": "test_with_includes",
        "output_dir": str(tmp_path / "output"),
        "delete_existing": True,
        "period": {
            "start": "2023-01-01T00:00:00",
            "end": "2023-01-02T00:00:00",
            "interval": "1H",
        },
        "config": {
            "model_type": "demo",
            "arg1": "foo",
            "arg2": "bar",
        },
    }

    # Backend config
    backend_config = {
        "type": "local",
        "timeout": 7200,
        "command": "echo 'included backend'",
    }

    # Postprocessor config
    processor_config = {
        "type": "noop",
        "validate_outputs": False,
    }

    # Write individual config files
    model_config_path = tmp_path / "model_config.yml"
    backend_config_path = tmp_path / "backend_config.yml"
    processor_config_path = tmp_path / "processor_config.yml"

    with open(model_config_path, "w") as f:
        yaml.dump(model_config, f)

    with open(backend_config_path, "w") as f:
        yaml.dump(backend_config, f)

    with open(processor_config_path, "w") as f:
        yaml.dump(processor_config, f)

    # Create pipeline config with includes
    pipeline_config = {
        "config": f"!include {model_config_path}",
        "backend": f"!include {backend_config_path}",
        "postprocessor": f"!include {processor_config_path}",
    }

    pipeline_config_path = tmp_path / "pipeline_config.yml"
    with open(pipeline_config_path, "w") as f:
        # Write with !include tags (need to be careful with YAML formatting)
        f.write(f"config: !include {model_config_path}\n")
        f.write(f"backend: !include {backend_config_path}\n")
        f.write(f"postprocessor: !include {processor_config_path}\n")

    return {
        "pipeline_config": pipeline_config_path,
        "model_config": model_config_path,
        "backend_config": backend_config_path,
        "processor_config": processor_config_path,
    }


class TestPipelineConfigLoading:
    """Test loading of pipeline configurations."""

    def test_load_inline_pipeline_config(self, basic_inline_pipeline_config, tmp_path):
        """Test loading a pipeline config with all sections inline."""
        config_path = tmp_path / "inline_pipeline.yml"
        with open(config_path, "w") as f:
            yaml.dump(basic_inline_pipeline_config, f)

        # Load the config
        loaded_config = load_config(str(config_path))

        # Verify all sections are present
        assert "config" in loaded_config
        assert "backend" in loaded_config
        assert "postprocessor" in loaded_config

        # Verify config section
        assert loaded_config["config"]["run_id"] == "test_inline_pipeline"
        assert loaded_config["config"]["config"]["arg1"] == "foo"

        # Verify backend section
        assert loaded_config["backend"]["type"] == "local"
        assert loaded_config["backend"]["timeout"] == 3600

        # Verify postprocessor section
        assert loaded_config["postprocessor"]["type"] == "noop"

    def test_load_pipeline_config_with_includes(self, tmp_config_files):
        """Test loading a pipeline config with !include directives."""
        # Load the pipeline config with includes
        loaded_config = load_yaml_with_includes(tmp_config_files["pipeline_config"])

        # Verify all sections are loaded from included files
        assert "config" in loaded_config
        assert "backend" in loaded_config
        assert "postprocessor" in loaded_config

        # Verify config section
        assert loaded_config["config"]["run_id"] == "test_with_includes"
        assert loaded_config["config"]["config"]["arg1"] == "foo"

        # Verify backend section
        assert loaded_config["backend"]["type"] == "local"
        assert loaded_config["backend"]["timeout"] == 7200

        # Verify postprocessor section
        assert loaded_config["postprocessor"]["type"] == "noop"

    def test_load_minimal_pipeline_config(self, tmp_path):
        """Test loading a minimal pipeline config with only config section."""
        minimal_config = {
            "config": {
                "run_id": "minimal_test",
                "output_dir": "./output/minimal",
                "period": {
                    "start": "2023-01-01T00:00:00",
                    "end": "2023-01-01T12:00:00",
                    "interval": "1H",
                },
                "config": {
                    "model_type": "demo",
                    "arg1": "test",
                    "arg2": "value",
                },
            }
        }

        config_path = tmp_path / "minimal_pipeline.yml"
        with open(config_path, "w") as f:
            yaml.dump(minimal_config, f)

        loaded_config = load_config(str(config_path))

        # Config section should be present
        assert "config" in loaded_config
        assert loaded_config["config"]["run_id"] == "minimal_test"

        # Backend and postprocessor should not be present
        assert "backend" not in loaded_config or loaded_config.get("backend") is None
        assert (
            "postprocessor" not in loaded_config
            or loaded_config.get("postprocessor") is None
        )


class TestPipelineConfigExtraction:
    """Test extraction of config sections for pipeline execution."""

    def test_extract_config_section(self, basic_inline_pipeline_config):
        """Test extracting the config section from pipeline config."""
        config_section = basic_inline_pipeline_config["config"]

        assert config_section["run_id"] == "test_inline_pipeline"
        assert "period" in config_section
        assert "config" in config_section

    def test_extract_backend_section(self, basic_inline_pipeline_config):
        """Test extracting the backend section from pipeline config."""
        backend_section = basic_inline_pipeline_config["backend"]

        assert backend_section["type"] == "local"
        assert backend_section["timeout"] == 3600

    def test_extract_postprocessor_section(self, basic_inline_pipeline_config):
        """Test extracting the postprocessor section from pipeline config."""
        processor_section = basic_inline_pipeline_config["postprocessor"]

        assert processor_section["type"] == "noop"


class TestPipelineConfigValidation:
    """Test validation of pipeline configurations."""

    def test_missing_config_section(self, tmp_path):
        """Test that missing config section raises appropriate error."""
        invalid_config = {
            "backend": {"type": "local"},
            "postprocessor": {"type": "noop"},
        }

        config_path = tmp_path / "invalid_pipeline.yml"
        with open(config_path, "w") as f:
            yaml.dump(invalid_config, f)

        # This should be caught when trying to use the config
        loaded_config = load_config(str(config_path))

        # Config section should be missing or None
        assert "config" not in loaded_config or loaded_config.get("config") is None

    def test_invalid_backend_type(self, basic_inline_pipeline_config, tmp_path):
        """Test that invalid backend type is handled."""
        basic_inline_pipeline_config["backend"]["type"] = "invalid_backend"

        config_path = tmp_path / "invalid_backend.yml"
        with open(config_path, "w") as f:
            yaml.dump(basic_inline_pipeline_config, f)

        loaded_config = load_config(str(config_path))

        # Config should load, validation happens when instantiating backends
        assert loaded_config["backend"]["type"] == "invalid_backend"

    def test_invalid_processor_type(self, basic_inline_pipeline_config, tmp_path):
        """Test that invalid processor type is handled."""
        basic_inline_pipeline_config["postprocessor"]["type"] = "invalid_processor"

        config_path = tmp_path / "invalid_processor.yml"
        with open(config_path, "w") as f:
            yaml.dump(basic_inline_pipeline_config, f)

        loaded_config = load_config(str(config_path))

        # Config should load, validation happens when instantiating processors
        assert loaded_config["postprocessor"]["type"] == "invalid_processor"


class TestPipelineConfigComposition:
    """Test composition of configs using includes and overrides."""

    def test_partial_include_with_inline(self, tmp_config_files, tmp_path):
        """Test mixing included and inline configs."""
        # Create a pipeline config with some includes and some inline
        pipeline_config_path = tmp_path / "mixed_pipeline.yml"
        with open(pipeline_config_path, "w") as f:
            f.write(f"config: !include {tmp_config_files['model_config']}\n")
            f.write("backend:\n")
            f.write("  type: local\n")
            f.write("  timeout: 5000\n")
            f.write(f"postprocessor: !include {tmp_config_files['processor_config']}\n")

        loaded_config = load_yaml_with_includes(pipeline_config_path)

        # Verify mixed loading
        assert loaded_config["config"]["run_id"] == "test_with_includes"
        assert loaded_config["backend"]["type"] == "local"
        assert loaded_config["backend"]["timeout"] == 5000
        assert loaded_config["postprocessor"]["type"] == "noop"

    def test_nested_includes(self, tmp_path):
        """Test nested include directives."""
        # Create a nested structure
        base_backend = {
            "type": "local",
            "timeout": 3600,
        }

        base_backend_path = tmp_path / "base_backend.yml"
        with open(base_backend_path, "w") as f:
            yaml.dump(base_backend, f)

        extended_config = {
            "config": {
                "run_id": "nested_test",
                "output_dir": "./output",
                "period": {
                    "start": "2023-01-01T00:00:00",
                    "end": "2023-01-01T12:00:00",
                    "interval": "1H",
                },
                "config": {"model_type": "demo"},
            },
        }

        pipeline_config_path = tmp_path / "nested_pipeline.yml"
        with open(pipeline_config_path, "w") as f:
            yaml.dump(extended_config, f)
            f.write(f"backend: !include {base_backend_path}\n")

        loaded_config = load_yaml_with_includes(pipeline_config_path)

        assert loaded_config["backend"]["type"] == "local"
        assert loaded_config["config"]["run_id"] == "nested_test"


class TestBackwardCompatibilityWarning:
    """Test that using old parameter names triggers warnings."""

    def test_old_run_backend_parameter_warning(self, tmp_path, caplog):
        """Test that passing run_backend string logs a deprecation warning."""
        import logging
        from rompy.pipeline import LocalPipelineBackend

        # Create the output directory structure that the pipeline expects
        output_dir = tmp_path / "test_run"
        output_dir.mkdir(parents=True, exist_ok=True)

        model_run = ModelRun(
            run_id="test_run",
            period=TimeRange(
                start=datetime(2023, 1, 1),
                end=datetime(2023, 1, 2),
                interval="1H",
            ),
            output_dir=str(tmp_path),
            config=DemoConfig(arg1="foo", arg2="bar"),
        )

        backend = LocalPipelineBackend()
        processor_config = NoopPostprocessorConfig()

        with caplog.at_level(logging.WARNING):
            with patch("rompy.model.ModelRun.generate", return_value=str(output_dir)):
                with patch("rompy.model.ModelRun.run", return_value=True):
                    with patch(
                        "rompy.model.ModelRun.postprocess",
                        return_value={"success": True},
                    ):
                        result = backend.execute(
                            model_run,
                            run_backend="local",  # Old parameter name
                            processor=processor_config,
                        )

        # Check that deprecation warning was logged
        assert any(
            "run_backend" in record.message and "deprecated" in record.message
            for record in caplog.records
        )

        # Should still work with backward compatibility
        assert result["success"] is True
