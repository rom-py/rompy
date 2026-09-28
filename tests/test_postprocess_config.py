"""
Tests for postprocessor configuration framework.

This module tests the postprocessor config classes, loading, and validation.
"""

import json

import pytest
import yaml

from rompy.postprocess import (
    BasePostprocessorConfig,
    NoopPostprocessorConfig,
    ProcessorConfig,
)
from rompy.postprocess.config import (
    _load_processor_config,
    _load_processor_config_from_dict,
    _processor_config_entry_points,
    validate_postprocessor_config,
)
from rompy.core.responses import (
    PostprocessSuccess,
    PostprocessFailure,
)


class TestBasePostprocessorConfig:
    """Tests for BasePostprocessorConfig abstract base class."""

    def test_is_abstract(self):
        """Test that BasePostprocessorConfig cannot be instantiated."""
        with pytest.raises(TypeError):
            BasePostprocessorConfig()

    def test_can_subclass(self):
        """Test that BasePostprocessorConfig can be subclassed."""

        class TestConfig(BasePostprocessorConfig):
            type: str = "test"

            def get_postprocessor_class(self):
                return object

        # Should not raise
        config = TestConfig()
        assert config.timeout == 3600
        assert config.env_vars == {}
        assert config.working_dir is None


class TestNoopPostprocessorConfig:
    """Tests for NoopPostprocessorConfig concrete class."""

    def test_default_values(self):
        """Test default values are set correctly."""
        config = NoopPostprocessorConfig()
        assert config.type == "noop"
        assert config.validate_outputs is True
        assert config.timeout == 3600
        assert config.env_vars == {}
        assert config.working_dir is None

    def test_custom_values(self):
        """Test custom values can be set."""
        config = NoopPostprocessorConfig(
            validate_outputs=False,
            timeout=7200,
            env_vars={"DEBUG": "1"},
        )
        assert config.validate_outputs is False
        assert config.timeout == 7200
        assert config.env_vars == {"DEBUG": "1"}

    def test_validation_rejects_invalid_timeout(self):
        """Test that invalid timeout values are rejected."""
        with pytest.raises(ValueError):
            NoopPostprocessorConfig(timeout=30)  # Below minimum

        with pytest.raises(ValueError):
            NoopPostprocessorConfig(timeout=90000)  # Above maximum

    def test_get_postprocessor_class(self):
        """Test that get_postprocessor_class returns NoopPostprocessor."""
        from rompy.postprocess import NoopPostprocessor

        config = NoopPostprocessorConfig()
        processor_class = config.get_postprocessor_class()
        assert processor_class is NoopPostprocessor


class TestLoadProcessorConfig:
    """Tests for _load_processor_config function."""

    def test_load_from_yaml(self, tmp_path):
        """Test loading config from YAML file."""
        config_file = tmp_path / "test_config.yml"
        config_data = {"type": "noop", "validate_outputs": False}
        config_file.write_text(yaml.dump(config_data))

        config = _load_processor_config(config_file)
        assert isinstance(config, NoopPostprocessorConfig)
        assert config.type == "noop"
        assert config.validate_outputs is False

    def test_load_from_json(self, tmp_path):
        """Test loading config from JSON file."""
        config_file = tmp_path / "test_config.json"
        config_data = {"type": "noop", "timeout": 7200}
        config_file.write_text(json.dumps(config_data))

        config = _load_processor_config(config_file)
        assert isinstance(config, NoopPostprocessorConfig)
        assert config.timeout == 7200

    def test_file_not_found(self, tmp_path):
        """Test error when file doesn't exist."""
        config_file = tmp_path / "nonexistent.yml"

        with pytest.raises(FileNotFoundError):
            _load_processor_config(config_file)

    def test_missing_type_field(self, tmp_path):
        """Test error when type field is missing."""
        config_file = tmp_path / "bad_config.yml"
        config_file.write_text(yaml.dump({"validate_outputs": True}))

        with pytest.raises(ValueError, match="type"):
            _load_processor_config(config_file)

    def test_unknown_processor_type(self, tmp_path):
        """Test error for unknown processor type."""
        config_file = tmp_path / "unknown_config.yml"
        config_file.write_text(yaml.dump({"type": "unknown"}))

        with pytest.raises(ValueError, match="Unknown processor type"):
            _load_processor_config(config_file)


class _FakeEntryPoint:
    def __init__(self, name, value):
        self.name = name
        self.value = value

    def load(self):
        return NoopPostprocessorConfig


class _ModernEntryPoints(list):
    def select(self, *, group):
        assert group == "rompy.postprocess.config"
        return self


class TestConfigEntryPointDiscovery:
    def test_reversed_duplicate_names_raise_deterministically(self, monkeypatch, tmp_path):
        entries = _ModernEntryPoints(
            [
                _FakeEntryPoint("duplicate", "provider-b:Config"),
                _FakeEntryPoint("duplicate", "provider-a:Config"),
            ]
        )
        monkeypatch.setattr("importlib.metadata.entry_points", lambda: entries)

        with pytest.raises(ValueError) as first:
            _load_processor_config_from_dict({"type": "duplicate"})
        monkeypatch.setattr(
            "importlib.metadata.entry_points",
            lambda: _ModernEntryPoints(list(reversed(entries))),
        )
        config_file = tmp_path / "duplicate.yml"
        config_file.write_text("type: duplicate\n")
        with pytest.raises(ValueError) as second:
            _load_processor_config(config_file)

        assert str(first.value) == str(second.value)
        assert "duplicate" in str(first.value)
        assert "provider-a:Config" in str(first.value)
        assert "provider-b:Config" in str(first.value)

    @pytest.mark.parametrize("legacy_shape", ["dict", "group_argument"])
    def test_legacy_duplicate_names_raise(self, monkeypatch, legacy_shape):
        entries = [
            _FakeEntryPoint("duplicate", "provider-b:Config"),
            _FakeEntryPoint("duplicate", "provider-a:Config"),
        ]
        if legacy_shape == "dict":
            monkeypatch.setattr(
                "importlib.metadata.entry_points",
                lambda: {"rompy.postprocess.config": entries},
            )
        else:
            def legacy_entry_points(*, group=None):
                if group is None:
                    raise TypeError("group is required")
                return entries

            monkeypatch.setattr("importlib.metadata.entry_points", legacy_entry_points)

        with pytest.raises(ValueError, match="Ambiguous postprocessor config"):
            _processor_config_entry_points()


class TestValidatePostprocessorConfig:
    """Tests for validate_postprocessor_config function."""

    def test_valid_config(self, tmp_path):
        """Test validation passes for valid config."""
        config_file = tmp_path / "valid_config.yml"
        config_file.write_text(yaml.dump({"type": "noop"}))

        is_valid, message, config = validate_postprocessor_config(config_file)
        assert is_valid is True
        assert "Valid" in message
        assert isinstance(config, NoopPostprocessorConfig)

    def test_type_mismatch(self, tmp_path):
        """Test validation fails when type doesn't match expected."""
        config_file = tmp_path / "config.yml"
        config_file.write_text(yaml.dump({"type": "noop"}))

        is_valid, message, config = validate_postprocessor_config(
            config_file, processor_type="other"
        )
        assert is_valid is False
        assert "does not match" in message
        assert config is None

    def test_file_not_found(self, tmp_path):
        """Test validation handles missing file."""
        config_file = tmp_path / "nonexistent.yml"

        is_valid, message, config = validate_postprocessor_config(config_file)
        assert is_valid is False
        assert "not found" in message
        assert config is None


class TestProcessorConfigTypeAlias:
    """Tests for ProcessorConfig type alias."""

    def test_is_union(self):
        """Test that ProcessorConfig is a Union type or single type."""
        import typing

        origin = typing.get_origin(ProcessorConfig)
        # Union[SingleType] is optimized to just SingleType
        assert origin is typing.Union or ProcessorConfig is NoopPostprocessorConfig

    def test_includes_noop(self):
        """Test that ProcessorConfig includes NoopPostprocessorConfig."""
        import typing

        args = typing.get_args(ProcessorConfig)
        # Union[SingleType] is optimized to just SingleType
        assert (
            NoopPostprocessorConfig in args
            or ProcessorConfig is NoopPostprocessorConfig
        )


class TestModelRunIntegration:
    """Integration tests for ModelRun.postprocess with config objects."""

    def test_postprocess_accepts_config(self):
        """Test that ModelRun.postprocess accepts config objects."""
        from rompy.core.time import TimeRange
        from rompy.model import ModelRun
        from datetime import datetime

        model = ModelRun(
            run_id="test",
            period=TimeRange(
                start=datetime(2020, 1, 1),
                end=datetime(2020, 1, 2),
                interval="1H",
            ),
        )

        config = NoopPostprocessorConfig(validate_outputs=False)
        # Should not raise TypeError
        result = model.postprocess(config)
        # Result is now PostprocessResult type, not dict
        assert isinstance(result, (PostprocessSuccess, PostprocessFailure))

    def test_postprocess_rejects_string(self):
        """Test that ModelRun.postprocess rejects string processor names."""
        from rompy.core.time import TimeRange
        from rompy.model import ModelRun
        from datetime import datetime

        model = ModelRun(
            run_id="test",
            period=TimeRange(
                start=datetime(2020, 1, 1),
                end=datetime(2020, 1, 2),
                interval="1H",
            ),
        )

        # New behavior: returns PostprocessFailure instead of raising TypeError
        result = model.postprocess("noop")
        assert isinstance(result, PostprocessFailure)
        assert not result.success
        assert "BasePostprocessorConfig" in result.error
