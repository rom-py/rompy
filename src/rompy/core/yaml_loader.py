"""
YAML loader with support for !include directive.

This module provides a custom YAML loader that extends the standard safe_load
functionality with the ability to include external YAML files using the !include tag.

Example:
    config: !include model_config.yaml
    backend: !include backends/local.yaml
"""

import os
from pathlib import Path
from typing import Any, Dict, Set

import yaml


class IncludeLoader(yaml.SafeLoader):
    """Custom YAML loader with support for !include directive.

    This loader extends yaml.SafeLoader to add the !include constructor,
    which allows referencing external YAML files. It tracks the chain of
    included files to prevent circular dependencies.

    Features:
    - Relative path resolution from the including file's directory
    - Absolute path support
    - Circular dependency detection
    - Environment variable expansion in paths
    - Maximum include depth limit

    Attributes:
        _root_dir: Directory of the root YAML file being loaded
        _include_chain: Set of file paths already included (for cycle detection)
        _include_depth: Current nesting depth of includes
    """

    # Maximum allowed include depth to prevent infinite recursion
    MAX_INCLUDE_DEPTH = 10

    def __init__(self, stream):
        """Initialize the loader with stream and include tracking.

        Args:
            stream: YAML stream to load from
        """
        self._root_dir = Path.cwd()
        self._include_chain: Set[Path] = set()
        self._include_depth = 0

        # Try to get the directory of the file being loaded
        if hasattr(stream, "name"):
            self._root_dir = Path(stream.name).parent.resolve()

        super().__init__(stream)


def include_constructor(loader: IncludeLoader, node: yaml.Node) -> Any:
    """Constructor function for !include tag.

    This function is called by the YAML loader when it encounters an !include tag.
    It resolves the path, loads the referenced file, and returns its contents.

    Args:
        loader: The IncludeLoader instance
        node: The YAML node containing the include path

    Returns:
        The loaded content from the included file (dict, list, or scalar)

    Raises:
        yaml.YAMLError: If the file cannot be loaded or circular dependency detected
        FileNotFoundError: If the included file doesn't exist
        ValueError: If include depth exceeds maximum
    """
    # Check include depth
    if loader._include_depth >= IncludeLoader.MAX_INCLUDE_DEPTH:
        raise ValueError(
            f"Include depth exceeds maximum of {IncludeLoader.MAX_INCLUDE_DEPTH}. "
            "This may indicate a circular dependency or overly nested includes."
        )

    # Get the path from the node
    include_path = loader.construct_scalar(node)

    # Expand environment variables in the path
    include_path = os.path.expandvars(include_path)

    # Resolve the path relative to the current file's directory
    if not os.path.isabs(include_path):
        include_path = loader._root_dir / include_path
    else:
        include_path = Path(include_path)

    # Resolve to absolute path to check for circular dependencies
    include_path = include_path.resolve()

    # Check if file exists
    if not include_path.exists():
        raise FileNotFoundError(
            f"Included file not found: {include_path}\n"
            f"Referenced from: {loader._root_dir}"
        )

    # Check for circular dependencies
    if include_path in loader._include_chain:
        chain_str = " -> ".join(str(p) for p in loader._include_chain)
        raise yaml.YAMLError(
            f"Circular include detected: {include_path}\n"
            f"Include chain: {chain_str} -> {include_path}"
        )

    # Add to include chain
    loader._include_chain.add(include_path)
    loader._include_depth += 1

    try:
        # Load the included file with a fresh file handle
        with open(include_path, "r") as f:
            # Read the content
            content = f.read()

        # Create a StringIO for the content
        from io import StringIO

        stream = StringIO(content)

        # Create a new loader that inherits the include chain
        included_loader = IncludeLoader(stream)
        included_loader._root_dir = include_path.parent
        included_loader._include_chain = loader._include_chain.copy()
        included_loader._include_depth = loader._include_depth

        # Load and return the content
        result = included_loader.get_single_data()
        stream.close()
        return result

    finally:
        # Remove from include chain when done
        loader._include_chain.discard(include_path)
        loader._include_depth -= 1


# Register the include constructor
IncludeLoader.add_constructor("!include", include_constructor)


def load_yaml_with_includes(stream) -> Dict[str, Any]:
    """Load a YAML file with support for !include directives.

    This is the main entry point for loading YAML files that may contain
    !include tags. It uses the custom IncludeLoader to handle includes.

    Args:
        stream: File path (str/Path) or file-like object to load from

    Returns:
        Loaded YAML content as a dictionary

    Raises:
        FileNotFoundError: If the file doesn't exist
        yaml.YAMLError: If the YAML is invalid or includes have errors

    Example:
        >>> content = load_yaml_with_includes('pipeline.yaml')
        >>> print(content['config'])
    """
    # If stream is a string or Path, open it as a file
    if isinstance(stream, (str, Path)):
        stream = Path(stream)
        if not stream.exists():
            raise FileNotFoundError(f"YAML file not found: {stream}")

        with open(stream, "r") as f:
            return yaml.load(f, Loader=IncludeLoader)
    else:
        # Assume it's a file-like object
        return yaml.load(stream, Loader=IncludeLoader)


def safe_load_with_includes(content: str, root_dir: Path = None) -> Dict[str, Any]:
    """Load YAML content from a string with include support.

    This function is useful when you have YAML content as a string but
    still want to support includes. You can specify a root directory for
    resolving relative paths.

    Args:
        content: YAML content as a string
        root_dir: Directory to use for resolving relative includes (default: cwd)

    Returns:
        Loaded YAML content as a dictionary

    Example:
        >>> yaml_str = "config: !include model.yaml"
        >>> content = safe_load_with_includes(yaml_str, Path('/configs'))
    """
    from io import StringIO

    stream = StringIO(content)
    loader = IncludeLoader(stream)

    if root_dir:
        loader._root_dir = Path(root_dir).resolve()

    try:
        return loader.get_single_data()
    finally:
        stream.close()
