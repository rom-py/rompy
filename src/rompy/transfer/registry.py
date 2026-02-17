"""Transfer registry for scheme-based dispatch."""

from __future__ import annotations

import importlib.metadata
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Type, Union

from .utils import parse_scheme

if TYPE_CHECKING:
    from .base import TransferBase

# Global registry cache
_REGISTRY: Dict[str, Type["TransferBase"]] | None = None


def _load_transfer_registry() -> Dict[str, Type["TransferBase"]]:
    """
    Load transfer implementations from entry points.

    Returns:
        Dict mapping scheme names (lowercase) to TransferBase classes.

    Raises:
        ValueError: If duplicate schemes are found.
    """
    registry: Dict[str, Type["TransferBase"]] = {}
    seen_schemes: Dict[str, str] = {}  # scheme -> entry_point_name

    # Load entry points from rompy.transfer group
    entry_points = importlib.metadata.entry_points(group="rompy.transfer")

    for ep in entry_points:
        scheme = ep.name.lower()

        # Check for duplicates
        if scheme in seen_schemes:
            raise ValueError(
                f"Duplicate transfer entry point for scheme '{scheme}': "
                f"'{seen_schemes[scheme]}' and '{ep.name}'"
            )

        seen_schemes[scheme] = ep.name

        # Load the transfer class
        try:
            transfer_class = ep.load()
            registry[scheme] = transfer_class
        except Exception as e:
            # Log warning but don't fail - allow optional transfers
            import warnings

            warnings.warn(
                f"Failed to load transfer for scheme '{scheme}' from entry point '{ep.name}': {e}",
                UserWarning,
            )

    return registry


def get_registry() -> Dict[str, Type["TransferBase"]]:
    """
    Get the cached transfer registry.

    Lazy-loads the registry on first access.
    """
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = _load_transfer_registry()
    return _REGISTRY


def get_transfer(uri_or_pathlike: Union[str, Path, Any]) -> "TransferBase":
    """
    Get a transfer instance for the given URI or path-like object.

    Args:
        uri_or_pathlike: URI string, Path, or cloudpathlib.AnyPath object

    Returns:
        Instantiated transfer object for the scheme

    Raises:
        KeyError: If no transfer is registered for the URI's scheme
    """
    # Convert Path-like objects to string URIs
    if isinstance(uri_or_pathlike, Path):
        uri = str(uri_or_pathlike)
    elif hasattr(uri_or_pathlike, "__str__"):
        # Handle cloudpathlib.AnyPath and other path-like objects
        uri = str(uri_or_pathlike)
    else:
        uri = uri_or_pathlike

    # Parse the scheme
    scheme = parse_scheme(uri)

    # Look up transfer class in registry
    registry = get_registry()
    if scheme not in registry:
        available = ", ".join(sorted(registry.keys()))
        raise KeyError(
            f"No transfer registered for scheme '{scheme}'. "
            f"Available schemes: {available}"
        )

    # Instantiate and return the transfer
    transfer_class = registry[scheme]
    return transfer_class()
