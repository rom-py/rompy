"""
Postprocessor configuration classes for ROMPY.

This module provides Pydantic-based configuration classes for different
postprocessor types. These configurations handle transient execution parameters
while maintaining type safety and validation.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, Dict, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator

if TYPE_CHECKING:
    from . import NoopPostprocessor


class BasePostprocessorConfig(BaseModel, ABC):
    """Base class for all postprocessor configurations.

    This class defines common configuration parameters that apply to all
    postprocessor types, such as timeouts and environment variables.
    """

    timeout: int = Field(
        3600,
        ge=60,
        le=86400,
        description="Maximum execution time in seconds (1 minute to 24 hours)",
    )

    env_vars: Dict[str, str] = Field(
        default_factory=dict,
        description="Additional environment variables to set during execution",
    )

    working_dir: Optional[Path] = Field(
        None,
        description="Working directory for execution (defaults to model output directory)",
    )

    model_config = ConfigDict(
        validate_assignment=True,
        extra="forbid",  # Don't allow extra fields
        use_enum_values=True,
    )

    @field_validator("working_dir")
    @classmethod
    def validate_working_dir(cls, v):
        """Validate working directory exists if specified."""
        if v is not None:
            path = Path(v)
            if not path.exists():
                raise ValueError(f"Working directory does not exist: {path}")
            if not path.is_dir():
                raise ValueError(f"Working directory is not a directory: {path}")
        return v

    @field_validator("env_vars")
    @classmethod
    def validate_env_vars(cls, v):
        """Validate environment variables."""
        if not isinstance(v, dict):
            raise ValueError("env_vars must be a dictionary")

        for key, value in v.items():
            if not isinstance(key, str) or not isinstance(value, str):
                raise ValueError("Environment variable keys and values must be strings")
            if not key:
                raise ValueError("Environment variable keys cannot be empty")

        return v

    @abstractmethod
    def get_postprocessor_class(self):
        """Return the postprocessor class that should handle this configuration.

        Returns:
            The postprocessor class to use for execution
        """
        pass


class NoopPostprocessorConfig(BasePostprocessorConfig):
    """Configuration for no-operation postprocessor.

    This configuration is used when no postprocessing is required but output
    validation may still be needed. It provides the simplest postprocessor
    that can optionally validate that model outputs exist.
    """

    type: Literal["noop"] = "noop"

    validate_outputs: bool = Field(
        True, description="Whether to validate that expected outputs exist"
    )

    def get_postprocessor_class(self):
        """Return the NoopPostprocessor class."""
        from . import NoopPostprocessor

        return NoopPostprocessor

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "type": "noop",
                    "timeout": 3600,
                    "validate_outputs": True,
                },
                {
                    "type": "noop",
                    "timeout": 1800,
                    "validate_outputs": False,
                    "env_vars": {"DEBUG": "1"},
                },
                {"type": "noop", "working_dir": "/path/to/output/dir"},
            ]
        }
    )


# Type alias for all postprocessor configurations
ProcessorConfig = Union[NoopPostprocessorConfig]


def _load_processor_config(config_file):
    """Load postprocessor configuration from a YAML or JSON file.

    This function reads a configuration file, extracts the processor type,
    and instantiates the appropriate configuration class using entry points.

    Args:
        config_file: Path to the configuration file (YAML or JSON)

    Returns:
        An instance of the appropriate postprocessor config class

    Raises:
        ValueError: If the processor type is not found in registered entry points
        FileNotFoundError: If the config file doesn't exist
        yaml.YAMLError: If the file is neither valid JSON nor valid YAML
    """
    import json
    from importlib.metadata import entry_points

    path = Path(config_file)

    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {config_file}")

    content = path.read_text()

    # Try JSON first, then YAML
    try:
        config_data = json.loads(content)
    except json.JSONDecodeError:
        import yaml

        config_data = yaml.safe_load(content)

    if not isinstance(config_data, dict):
        raise ValueError(
            f"Config file must contain a dictionary, got {type(config_data)}"
        )

    processor_type = config_data.pop("type", None)

    if processor_type is None:
        raise ValueError("Config file must contain a 'type' field")

    # Load from entry point
    eps = entry_points(group="rompy.postprocess.config")
    for ep in eps:
        if ep.name == processor_type:
            config_class = ep.load()
            return config_class(**config_data)

    # If we get here, type wasn't found
    available = [ep.name for ep in eps]
    if available:
        available_str = ", ".join(available)
        raise ValueError(
            f"Unknown processor type: '{processor_type}'. Available types: {available_str}"
        )
    else:
        raise ValueError(
            f"Unknown processor type: '{processor_type}'. No postprocessor types are registered."
        )


def validate_postprocessor_config(config_file, processor_type=None):
    """Validate a postprocessor configuration file.

    This function validates that a configuration file is valid YAML/JSON,
    contains a valid processor type, and can be instantiated.

    Args:
        config_file: Path to the configuration file to validate
        processor_type: Optional specific processor type to validate against.
                       If None, validates against the type in the config.

    Returns:
        Tuple of (is_valid: bool, message: str, config: Optional[BasePostprocessorConfig])
    """
    try:
        config = _load_processor_config(config_file)

        if processor_type is not None and config.type != processor_type:
            return (
                False,
                f"Config type '{config.type}' does not match expected type '{processor_type}'",
                None,
            )

        return (True, f"Valid {config.type} configuration", config)

    except FileNotFoundError as e:
        return (False, f"Config file not found: {e}", None)
    except ValueError as e:
        return (False, f"Validation error: {e}", None)
    except Exception as e:
        return (False, f"Unexpected error: {e}", None)
