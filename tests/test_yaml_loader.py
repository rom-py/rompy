"""
Tests for YAML loader with include support.
"""

import os
import tempfile
from pathlib import Path

import pytest
import yaml

from rompy.core.yaml_loader import (
    IncludeLoader,
    load_yaml_with_includes,
    safe_load_with_includes,
)


@pytest.fixture
def temp_yaml_dir(tmp_path):
    """Create a temporary directory with test YAML files."""
    return tmp_path


def test_basic_include(temp_yaml_dir):
    """Test basic file inclusion."""
    # Create included file
    included = temp_yaml_dir / "included.yaml"
    included.write_text("key1: value1\nkey2: value2\n")

    # Create main file with include
    main = temp_yaml_dir / "main.yaml"
    main.write_text("config: !include included.yaml\n")

    # Load and verify
    result = load_yaml_with_includes(main)
    assert result == {"config": {"key1": "value1", "key2": "value2"}}


def test_absolute_path_include(temp_yaml_dir):
    """Test inclusion with absolute path."""
    # Create included file
    included = temp_yaml_dir / "included.yaml"
    included.write_text("data: test\n")

    # Create main file with absolute path include
    main = temp_yaml_dir / "main.yaml"
    main.write_text(f"config: !include {included}\n")

    # Load and verify
    result = load_yaml_with_includes(main)
    assert result == {"config": {"data": "test"}}


def test_relative_path_include(temp_yaml_dir):
    """Test inclusion with relative path in subdirectory."""
    # Create subdirectory with included file
    subdir = temp_yaml_dir / "configs"
    subdir.mkdir()
    included = subdir / "included.yaml"
    included.write_text("nested: data\n")

    # Create main file with relative include
    main = temp_yaml_dir / "main.yaml"
    main.write_text("config: !include configs/included.yaml\n")

    # Load and verify
    result = load_yaml_with_includes(main)
    assert result == {"config": {"nested": "data"}}


def test_nested_include(temp_yaml_dir):
    """Test nested includes (include within include)."""
    # Create deepest file
    level2 = temp_yaml_dir / "level2.yaml"
    level2.write_text("deep: value\n")

    # Create middle file that includes level2
    level1 = temp_yaml_dir / "level1.yaml"
    level1.write_text("middle: !include level2.yaml\n")

    # Create main file that includes level1
    main = temp_yaml_dir / "main.yaml"
    main.write_text("top: !include level1.yaml\n")

    # Load and verify
    result = load_yaml_with_includes(main)
    assert result == {"top": {"middle": {"deep": "value"}}}


def test_multiple_includes(temp_yaml_dir):
    """Test multiple includes in same file."""
    # Create multiple included files
    config1 = temp_yaml_dir / "config1.yaml"
    config1.write_text("data1: value1\n")

    config2 = temp_yaml_dir / "config2.yaml"
    config2.write_text("data2: value2\n")

    # Create main file with multiple includes
    main = temp_yaml_dir / "main.yaml"
    main.write_text(
        """
config: !include config1.yaml
backend: !include config2.yaml
"""
    )

    # Load and verify
    result = load_yaml_with_includes(main)
    assert result == {"config": {"data1": "value1"}, "backend": {"data2": "value2"}}


def test_include_with_inline_content(temp_yaml_dir):
    """Test mixing includes with inline content."""
    # Create included file
    included = temp_yaml_dir / "backend.yaml"
    included.write_text("type: local\ntimeout: 3600\n")

    # Create main file mixing include and inline
    main = temp_yaml_dir / "main.yaml"
    main.write_text(
        """
config:
  run_id: test
  period: 1d
backend: !include backend.yaml
postprocessor:
  type: noop
  timeout: 1800
"""
    )

    # Load and verify
    result = load_yaml_with_includes(main)
    assert result["config"]["run_id"] == "test"
    assert result["backend"]["type"] == "local"
    assert result["postprocessor"]["type"] == "noop"


def test_missing_file_error(temp_yaml_dir):
    """Test error handling for missing included file."""
    main = temp_yaml_dir / "main.yaml"
    main.write_text("config: !include nonexistent.yaml\n")

    with pytest.raises(FileNotFoundError) as exc_info:
        load_yaml_with_includes(main)

    assert "nonexistent.yaml" in str(exc_info.value)


def test_circular_include_detection(temp_yaml_dir):
    """Test detection of circular includes."""
    # Create file1 that includes file2
    file1 = temp_yaml_dir / "file1.yaml"
    file1.write_text("data: !include file2.yaml\n")

    # Create file2 that includes file1 (circular)
    file2 = temp_yaml_dir / "file2.yaml"
    file2.write_text("data: !include file1.yaml\n")

    # Should raise error about circular dependency
    with pytest.raises(yaml.YAMLError) as exc_info:
        load_yaml_with_includes(file1)

    assert "Circular include" in str(exc_info.value)


def test_max_include_depth(temp_yaml_dir):
    """Test maximum include depth limit."""
    # Create a chain of includes exceeding max depth
    for i in range(12):  # Exceeds MAX_INCLUDE_DEPTH of 10
        if i < 11:
            content = f"data: !include file{i + 1}.yaml\n"
        else:
            content = "data: final\n"

        file = temp_yaml_dir / f"file{i}.yaml"
        file.write_text(content)

    # Should raise error about max depth
    with pytest.raises(ValueError) as exc_info:
        load_yaml_with_includes(temp_yaml_dir / "file0.yaml")

    assert "Include depth exceeds maximum" in str(exc_info.value)


def test_environment_variable_expansion(temp_yaml_dir):
    """Test environment variable expansion in include paths."""
    # Set environment variable
    os.environ["TEST_CONFIG_DIR"] = str(temp_yaml_dir)

    try:
        # Create included file
        included = temp_yaml_dir / "config.yaml"
        included.write_text("expanded: true\n")

        # Create main file with env var in path
        main = temp_yaml_dir / "main.yaml"
        main.write_text("config: !include $TEST_CONFIG_DIR/config.yaml\n")

        # Load and verify
        result = load_yaml_with_includes(main)
        assert result == {"config": {"expanded": True}}

    finally:
        # Clean up env var
        del os.environ["TEST_CONFIG_DIR"]


def test_safe_load_with_includes_string():
    """Test loading YAML from string with includes."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Create included file
        included = tmpdir / "data.yaml"
        included.write_text("value: 123\n")

        # Load from string
        yaml_content = "config: !include data.yaml\n"
        result = safe_load_with_includes(yaml_content, root_dir=tmpdir)

        assert result == {"config": {"value": 123}}


def test_include_preserves_data_types(temp_yaml_dir):
    """Test that includes preserve YAML data types."""
    # Create included file with various types
    included = temp_yaml_dir / "types.yaml"
    included.write_text(
        """
string: "text"
integer: 42
float: 3.14
boolean: true
null_value: null
list:
  - item1
  - item2
nested:
  key: value
"""
    )

    # Create main file
    main = temp_yaml_dir / "main.yaml"
    main.write_text("data: !include types.yaml\n")

    # Load and verify types
    result = load_yaml_with_includes(main)
    data = result["data"]

    assert data["string"] == "text"
    assert data["integer"] == 42
    assert data["float"] == 3.14
    assert data["boolean"] is True
    assert data["null_value"] is None
    assert data["list"] == ["item1", "item2"]
    assert data["nested"]["key"] == "value"


def test_include_scalar_value(temp_yaml_dir):
    """Test including a file with scalar value (not dict)."""
    # Create included file with scalar
    included = temp_yaml_dir / "scalar.yaml"
    included.write_text("just a string value\n")

    # Create main file
    main = temp_yaml_dir / "main.yaml"
    main.write_text("value: !include scalar.yaml\n")

    # Load and verify
    result = load_yaml_with_includes(main)
    assert result == {"value": "just a string value"}


def test_include_list_value(temp_yaml_dir):
    """Test including a file with list as root."""
    # Create included file with list
    included = temp_yaml_dir / "list.yaml"
    included.write_text(
        """
- item1
- item2
- item3
"""
    )

    # Create main file
    main = temp_yaml_dir / "main.yaml"
    main.write_text("items: !include list.yaml\n")

    # Load and verify
    result = load_yaml_with_includes(main)
    assert result == {"items": ["item1", "item2", "item3"]}


def test_file_not_found_main():
    """Test error when main file doesn't exist."""
    with pytest.raises(FileNotFoundError):
        load_yaml_with_includes("nonexistent_main.yaml")


def test_yaml_syntax_error_in_included_file(temp_yaml_dir):
    """Test handling of YAML syntax errors in included files."""
    # Create included file with invalid YAML (unclosed bracket)
    included = temp_yaml_dir / "invalid.yaml"
    included.write_text("key: [unclosed\n")

    # Create main file
    main = temp_yaml_dir / "main.yaml"
    main.write_text("config: !include invalid.yaml\n")

    # Should raise YAML error
    with pytest.raises(yaml.YAMLError):
        load_yaml_with_includes(main)
