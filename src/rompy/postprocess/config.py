"""
Postprocessor configuration classes for ROMPY.

This module provides Pydantic-based configuration classes for different
postprocessor types. These configurations handle transient execution parameters
while maintaining type safety and validation.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

if TYPE_CHECKING:
    pass


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

    def build_processor(self):
        """Construct the processor with this validated configuration."""
        processor_class = self.get_postprocessor_class()
        if processor_class is None:
            raise TypeError(f"{type(self).__name__} did not provide a processor class")
        return processor_class(self)

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


class PostprocessPipelineConfig(BaseModel):
    """Ordered processor configuration consumed by the core runner.

    Each item is either a validated processor config or a mapping containing a
    ``type`` field.  Mappings are resolved through the same canonical config
    entry-point group used by standalone processor configuration files.
    """

    type: Literal["pipeline"] = "pipeline"
    steps: list[Any] = Field(default_factory=list, min_length=1)
    failure_policy: Literal["fail_fast", "continue"] = "fail_fast"
    operational_state: dict[str, dict[str, Any]] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    @model_validator(mode="after")
    def resolve_steps(self):
        resolved = []
        for item in self.steps:
            if isinstance(item, BasePostprocessorConfig):
                resolved.append(item)
            elif isinstance(item, dict):
                resolved.append(_load_processor_config_from_dict(item))
            else:
                raise TypeError("pipeline steps must be processor configs or mappings")
        self.steps = resolved
        return self

    def build_steps(self):
        """Build ordered runtime processors without granting sidecar ownership."""
        return [config.build_processor() for config in self.steps]


# Type alias for all standalone postprocessor configurations.  The pipeline
# config is included so CLI and programmatic callers use one validated seam.
ProcessorConfig = Union[NoopPostprocessorConfig, PostprocessPipelineConfig]


_PROCESSOR_CONFIG_GROUP = "rompy.postprocess.config"


def _entry_point_provider_identity(entry_point) -> str:
    """Return a stable provider identity for ambiguity diagnostics."""
    distribution = getattr(entry_point, "dist", None)
    distribution_name = getattr(distribution, "name", None)
    if distribution_name is None and distribution is not None:
        metadata = getattr(distribution, "metadata", None)
        if metadata is not None:
            distribution_name = metadata.get("Name")
    target = getattr(entry_point, "value", None)
    if distribution_name and target:
        return f"{distribution_name} ({target})"
    if distribution_name:
        return str(distribution_name)
    if target:
        return str(target)
    module = getattr(entry_point, "module", None)
    attr = getattr(entry_point, "attr", None)
    if module and attr:
        return f"{module}:{attr}"
    if module:
        return str(module)
    return type(entry_point).__module__ + "." + type(entry_point).__qualname__


def _processor_config_entry_points():
    """Return deterministic config entry points from the canonical group.

    ``rompy.postprocess.config`` is the discovery group for validated config
    classes. The sibling ``rompy.postprocess`` group contains runtime
    implementations and is not consulted as a config registry. Compatibility
    branches support both modern and legacy ``importlib.metadata`` APIs.
    Duplicate names are rejected rather than resolved by metadata enumeration
    order.
    """
    from importlib.metadata import entry_points

    try:
        discovered = entry_points()
    except TypeError:  # pragma: no cover - legacy implementations
        discovered = entry_points(group=_PROCESSOR_CONFIG_GROUP)
    if hasattr(discovered, "select"):
        selected = discovered.select(group=_PROCESSOR_CONFIG_GROUP)
    elif isinstance(discovered, dict):  # pragma: no cover - Python 3.9 API
        selected = discovered.get(_PROCESSOR_CONFIG_GROUP, ())
    else:
        selected = discovered
    selected = tuple(selected)
    # Source checkouts and editable installs may have stale distribution
    # metadata.  Built-ins remain discoverable through the canonical group;
    # external providers still come exclusively from entry-point metadata.
    names = {item.name for item in selected}
    from importlib.metadata import EntryPoint
    builtins = []
    if "noop" not in names:
        builtins.append(EntryPoint("noop", "rompy.postprocess.config:NoopPostprocessorConfig", _PROCESSOR_CONFIG_GROUP))
    if "transfer" not in names:
        builtins.append(EntryPoint("transfer", "rompy.postprocess.transfer:TransferPostprocessorConfig", _PROCESSOR_CONFIG_GROUP))
    selected = selected + tuple(builtins)

    by_name = {}
    for entry_point in selected:
        by_name.setdefault(entry_point.name, []).append(entry_point)
    duplicates = {
        name: sorted(_entry_point_provider_identity(ep) for ep in entry_points)
        for name, entry_points in by_name.items()
        if len(entry_points) > 1
    }
    if duplicates:
        details = "; ".join(
            f"{name}: {', '.join(providers)}"
            for name, providers in sorted(duplicates.items())
        )
        raise ValueError(
            "Ambiguous postprocessor config entry point names; "
            f"duplicate providers ({details})"
        )

    return tuple(
        sorted(
            selected,
            key=lambda item: (item.name, _entry_point_provider_identity(item)),
        )
    )


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
        if "steps" in config_data:
            return PostprocessPipelineConfig(**config_data)
        raise ValueError("Config file must contain a 'type' field")
    if processor_type == "pipeline":
        return PostprocessPipelineConfig(**config_data)

    # Load from the canonical config entry-point group.
    eps = _processor_config_entry_points()
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


def _load_processor_config_from_dict(config_data: dict) -> BasePostprocessorConfig:
    """Load processor configuration from a dictionary.

    This function is used internally to instantiate processor configs from
    dictionary data (e.g., from inline config or already-parsed YAML).

    Args:
        config_data: Dictionary containing processor configuration with 'type' field

    Returns:
        An instance of the appropriate postprocessor config class

    Raises:
        ValueError: If the processor type is not found or config_data is invalid
    """
    if not isinstance(config_data, dict):
        raise ValueError(f"Config data must be a dictionary, got {type(config_data)}")

    # Make a copy to avoid modifying the original
    config_data = config_data.copy()

    processor_type = config_data.pop("type", None)

    if processor_type is None:
        # Pipeline documents intentionally have no processor ``type``; each
        # ordered item is discovered independently from the canonical group.
        if "steps" in config_data:
            return PostprocessPipelineConfig(**config_data)
        raise ValueError("Config must contain a 'type' field")
    if processor_type == "pipeline":
        return PostprocessPipelineConfig(**config_data)

    # Load from the canonical config entry-point group.
    eps = _processor_config_entry_points()
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
