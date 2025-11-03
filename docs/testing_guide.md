# Testing Guide

This guide provides comprehensive information on writing and running tests for Rompy, covering unit tests, integration tests, and best practices for test development.

## Overview of Testing in Rompy

Rompy uses pytest as its primary testing framework. The test suite is organized to validate:

1. **Unit tests**: Individual functions and classes
2. **Integration tests**: Multiple components working together
3. **End-to-end tests**: Complete workflows from configuration to execution

## Running Tests

### Prerequisites

Before running tests, ensure you have installed the development dependencies:

```bash
pip install -e .[dev]
```

### Running the Complete Test Suite

To run all tests:

```bash
pytest
```

To run tests with more verbose output:

```bash
pytest -v
```

### Running Specific Tests

To run tests for a specific module:

```bash
pytest tests/test_model.py
```

To run tests that match a pattern:

```bash
pytest -k "test_model_run"
```

To run tests with coverage:

```bash
pytest --cov=rompy --cov-report=html
```

### Test Categories

Rompy test suite is organized into different categories that can be run separately:

```bash
# Run only unit tests
pytest tests/unit/

# Run only integration tests
pytest tests/integration/

# Run tests with a specific marker
pytest -m "slow"  # Run slow tests
pytest -m "not slow"  # Run all tests except slow ones
```

## Writing Unit Tests

Unit tests focus on testing individual functions or methods in isolation.

### Basic Unit Test Structure

```python
import pytest
from rompy.core.config import BaseConfig

def test_base_config_creation():
    """Test creating a basic configuration."""
    config = BaseConfig()
    
    # Assertions
    assert config.model_type == "base"
    assert isinstance(config, BaseConfig)
```

### Testing with Pydantic Models

Since Rompy heavily uses Pydantic models, test for validation:

```python
import pytest
from pydantic import ValidationError
from rompy.core.config import BaseConfig

def test_config_validation():
    """Test configuration validation."""
    # Valid configuration
    config = BaseConfig(
        template="valid_template",
        checkout="valid_checkout"
    )
    assert config.template == "valid_template"
    
    # Invalid configuration should raise ValidationError
    with pytest.raises(ValidationError):
        BaseConfig(template="", checkout="")  # Empty strings may be invalid
```

### Testing with Fixtures

Use pytest fixtures to set up common test data:

```python
import pytest
from rompy.core.grid import RegularGrid

@pytest.fixture
def sample_grid():
    """Provide a sample grid for testing."""
    return RegularGrid(
        lon_min=-75.0, lon_max=-65.0,
        lat_min=35.0, lat_max=45.0,
        dx=0.1, dy=0.1
    )

def test_grid_properties(sample_grid):
    """Test grid properties."""
    assert sample_grid.lon_min == -75.0
    assert sample_grid.dx == 0.1
```

## Writing Integration Tests

Integration tests validate that multiple components work together correctly.

### Testing ModelRun Integration

```python
import pytest
from rompy.model import ModelRun
from rompy.core.config import BaseConfig
from rompy.core.time import TimeRange
from datetime import datetime

def test_model_run_integration(tmp_path):
    """Test ModelRun with configuration and time range."""
    # Create a temporary directory for outputs
    output_dir = tmp_path / "outputs"
    
    # Create a model run
    run = ModelRun(
        run_id="test_run",
        period=TimeRange(
            start=datetime(2023, 1, 1),
            end=datetime(2023, 1, 2),
            interval="1H"
        ),
        config=BaseConfig(),
        output_dir=output_dir,
    )
    
    # Test the generate method
    staging_dir = run.generate()
    
    # Assertions
    assert staging_dir.exists()
    assert staging_dir.name == "test_run"
    assert (output_dir / "test_run").exists()
```

### Testing with Different Backends

```python
import pytest
from unittest.mock import Mock, patch
from rompy.model import ModelRun
from rompy.backends import LocalConfig

def test_model_run_with_local_backend():
    """Test ModelRun with LocalConfig backend."""
    # Create a mock configuration
    config = Mock()
    config.model_type = "test"
    
    # Create a model run
    run = ModelRun(
        run_id="backend_test",
        config=config,
        # ... other parameters
    )
    
    # Create backend config
    backend_config = LocalConfig(
        timeout=300,
        command="echo test"
    )
    
    # Mock the backend's run method to avoid actually running a process
    with patch('rompy.run.local.LocalRunBackend.run') as mock_backend:
        mock_backend.return_value = True
        result = run.run(backend=backend_config)
    
    # Assertions
    assert result is True
    mock_backend.assert_called_once()
```

## Testing Best Practices

### 1. Use Descriptive Test Names

```python
# Good: Descriptive name that explains what is being tested
def test_time_range_validation_with_end_before_start_raises_error():
    pass

# Avoid: Generic names that don't explain the test purpose
def test_timerange():
    pass
```

### 2. Test Positive and Negative Cases

```python
def test_valid_configuration_succeeds():
    """Test that valid configuration is accepted."""
    config = BaseConfig(template="valid", checkout="valid")
    assert config.template == "valid"

def test_invalid_configuration_raises_error():
    """Test that invalid configuration raises appropriate error."""
    with pytest.raises(ValidationError):
        BaseConfig(template="", checkout="")  # Invalid due to empty values
```

### 3. Use Parametrize for Multiple Test Cases

```python
import pytest

@pytest.mark.parametrize("template,checkout,expected", [
    ("template1", "checkout1", True),
    ("template2", "checkout2", True),
    ("", "valid", False),  # Invalid case
    ("valid", "", False),  # Invalid case
])
def test_config_templates(template, checkout, expected):
    """Test various template and checkout combinations."""
    if expected:
        config = BaseConfig(template=template, checkout=checkout)
        assert config.template == template
    else:
        with pytest.raises(ValidationError):
            BaseConfig(template=template, checkout=checkout)
```

### 4. Test Edge Cases

```python
def test_time_range_with_same_start_and_end():
    """Test TimeRange with identical start and end times."""
    from datetime import datetime
    time_range = TimeRange(
        start=datetime(2023, 1, 1, 0, 0),
        end=datetime(2023, 1, 1, 0, 0),  # Same as start
        interval="1H"
    )
    # Depending on your implementation, this might be valid or raise an error
    # Test what behavior is expected
    assert time_range.start == time_range.end
```

## Testing Specific Components

### Testing Configuration Classes

```python
from pydantic import ValidationError
import pytest

def test_config_serialization():
    """Test that configurations can be serialized to dict."""
    config = BaseConfig(template="test", checkout="test")
    config_dict = config.model_dump()
    
    # Assert that we can create an identical config from the dict
    config_from_dict = BaseConfig(**config_dict)
    assert config.template == config_from_dict.template

def test_config_json_serialization():
    """Test that configurations can be serialized to JSON."""
    config = BaseConfig(template="test", checkout="test")
    json_str = config.model_dump_json()
    
    # Test deserialization
    from pydantic import TypeAdapter
    adapter = TypeAdapter(BaseConfig)
    deserialized = adapter.validate_json(json_str)
    
    assert config.template == deserialized.template
```

### Testing Backend Components

```python
def test_local_backend_timeout():
    """Test that LocalConfig enforces timeout."""
    backend_config = LocalConfig(
        timeout=1,  # 1 second timeout
        command="sleep 2"  # Command that takes 2 seconds
    )
    
    # This test would need to mock the actual execution 
    # to validate timeout behavior
    with patch('subprocess.run') as mock_run:
        # Setup mock to simulate long-running process
        mock_run.side_effect = lambda *args, **kwargs: time.sleep(2) or Mock(returncode=0)
        
        # Execute and verify timeout behavior
        # Implementation would depend on how timeout is handled in the actual backend
```

## Testing Model Extensions

When testing new model extensions:

```python
from mynewmodel.config import MyNewModelConfig

def test_mynewmodel_config():
    """Test custom model configuration."""
    config = MyNewModelConfig(
        # ... specific parameters for the model
    )
    
    # Test that the model type is correctly set
    assert config.model_type == "mynewmodel"
    
    # Test validation of custom parameters
    assert hasattr(config, 'custom_parameter')
```

## Mocking External Dependencies

Use mocking to isolate the code being tested:

```python
import pytest
from unittest.mock import Mock, patch

def test_data_source_integration():
    """Test data source without accessing external systems."""
    # Mock the external data access
    with patch('rompy.core.source.SourceFile._load_data') as mock_load:
        mock_load.return_value = Mock()  # Return mock data
        
        # Create and test the data source
        source = SourceFile(uri="dummy://test.nc", driver="netcdf")
        data = source.get_data()
        
        # Verify the mock was called as expected
        mock_load.assert_called_once()
```

## Performance Testing

For performance-related tests:

```python
import time
import pytest

def test_config_creation_performance():
    """Test that configuration creation is fast enough."""
    start_time = time.time()
    
    # Create many configurations
    configs = []
    for i in range(1000):
        config = BaseConfig(
            template=f"template_{i}",
            checkout=f"checkout_{i}"
        )
        configs.append(config)
    
    elapsed = time.time() - start_time
    
    # Assert that creation of 1000 configs takes less than 1 second
    assert elapsed < 1.0, f"Configuration creation too slow: {elapsed}s"
```

## Continuous Integration Testing

For CI/CD pipelines, you may want to organize tests with markers:

```python
import pytest

@pytest.mark.slow
def test_integration_workflow():
    """Slow integration test - mark to optionally skip in CI."""
    # Comprehensive integration test that takes a while
    pass

@pytest.mark.integration
def test_backend_integration():
    """Integration test for backend functionality."""
    # Test that requires backend dependencies
    pass
```

## Testing Commands and Utilities

```python
def test_cli_commands():
    """Test command line interface functionality."""
    from click.testing import CliRunner
    from rompy.cli import main  # Adjust import based on your CLI structure
    
    runner = CliRunner()
    result = runner.invoke(main, ['--help'])
    assert result.exit_code == 0
    assert 'Usage:' in result.output
```

## Code Coverage

### Measuring Coverage

To check code coverage:

```bash
# Generate coverage report
pytest --cov=rompy --cov-report=term-missing

# Generate HTML coverage report
pytest --cov=rompy --cov-report=html
```

### Coverage Best Practices

- Aim for high coverage (80%+ is generally good) but prioritize important code
- Focus on testing complex business logic and error conditions
- Don't artificially inflate coverage with meaningless tests

## Troubleshooting Common Testing Issues

### 1. Import Errors in Tests

If tests can't find the Rompy modules:

1. Make sure the package is installed in development mode: `pip install -e .`
2. Verify the Python path in your test environment

### 2. Mocking Issues

For complex mocking scenarios:

```python
from unittest.mock import patch, MagicMock

# For complex nested objects
with patch('module.Class.method') as mock_method, \
     patch('module.AnotherClass') as MockClass:
    MockClass.return_value = MagicMock()
    mock_method.return_value = expected_result
    
    # Execute your test
    result = your_function()
    
    # Assert expectations
    assert result == expected_result
```

### 3. Temp Directory Issues

Use pytest's `tmp_path` fixture for temporary files:

```python
def test_with_temp_directory(tmp_path):
    """Test that creates files in a temporary directory."""
    # Create a file in the temporary directory
    temp_file = tmp_path / "test_file.txt"
    temp_file.write_text("test content")
    
    # Use the file in your test
    assert temp_file.exists()
    assert temp_file.read_text() == "test content"
```

## Next Steps

- Review the existing tests in the `tests/` directory for more examples
- Follow the patterns used in existing tests for consistency
- Add tests for your new functionality following these guidelines
- Ensure all tests pass before submitting changes