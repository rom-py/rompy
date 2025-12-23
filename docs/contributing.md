# Contributing to Rompy

We welcome contributions from the community! This document provides guidelines and instructions for contributing to Rompy, including code changes, documentation improvements, bug fixes, and feature development.

## Code of Conduct

Please read and follow our [Code of Conduct](https://github.com/rom-py/rompy/blob/main/CODE_OF_CONDUCT.rst) to ensure a welcoming and inclusive environment for everyone.

## How to Contribute

There are several ways you can contribute to Rompy:

- Report bugs and suggest features via GitHub issues
- Contribute code through pull requests
- Improve documentation
- Review pull requests from other contributors
- Help answer questions in the issue tracker

## Development Setup

### Prerequisites

- Python 3.10 or higher
- Git
- A code editor or IDE of your choice
- Basic familiarity with command-line tools

### Setting Up Your Environment

1. Fork the repository on GitHub
2. Clone your fork:
   ```bash
   git clone https://github.com/YOUR-USERNAME/rompy.git
   cd rompy
   ```
3. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
4. Install the package in development mode:
   ```bash
   pip install -e .[dev]
   ```
5. Install pre-commit hooks:
   ```bash
   pre-commit install
   ```

## Making Code Changes

### Branch Strategy

1. Create a feature branch from `main`:
   ```bash
   git checkout main
   git pull origin main
   git checkout -b feature/your-feature-name
   ```
2. Make your changes in the new branch
3. Follow the project's coding style and conventions

### Code Style

Rompy follows the PEP 8 style guide and uses Black for code formatting. The pre-commit hooks will automatically format your code before commits.

- Use clear, descriptive variable and function names
- Write docstrings for all public functions and classes
- Include type hints where appropriate
- Follow the existing code style in the project

### Testing

All contributions should include appropriate tests:

1. Add unit tests for new functionality
2. Update existing tests if your changes affect current behavior
3. Run the test suite before submitting your pull request:
   ```bash
   pytest
   ```
4. Ensure all tests pass

### Documentation

When contributing code, update the documentation as needed:

1. Update docstrings to reflect code changes
2. Add or update examples in the documentation
3. Update the API documentation if adding new public interfaces

## Testing Procedures and Requirements

### Running Tests

To run the full test suite:
```bash
pytest
```

To run tests for a specific module:
```bash
pytest tests/test_module.py
```

To run tests with coverage:
```bash
pytest --cov=rompy
```

### Writing Tests

1. Place tests in the `tests/` directory following the same structure as the source code
2. Use descriptive test function names
3. Test both normal and edge cases
4. Mock external dependencies when appropriate 

### Test Requirements

- All new features must include appropriate unit tests
- Bug fixes should include regression tests
- Tests should have clear, descriptive names and assertions
- Aim for high code coverage, especially for critical functionality

## Debugging Techniques and Tools

### Using Python Debugger (pdb)

Add breakpoints in your code for debugging:
```python
import pdb; pdb.set_trace()
```

### Logging for Debugging

Use the Rompy logging system for debugging:
```python
from rompy.logging import get_logger
logger = get_logger(__name__)
logger.debug("Debug message with variable: %s", variable)
```

### Testing with Different Backends

Test your changes with different backends to ensure compatibility:
```python
# Test with local backend
success = model_run.run(backend=LocalConfig(...))

# Test with Docker backend
success = model_run.run(backend=DockerConfig(...))
```

## Code Review Process

### Pull Request Requirements

Before submitting a pull request:

1. Ensure all tests pass
2. Update documentation as needed
3. Add a clear description of the changes
4. Include issue references if applicable (e.g., "Fixes #123")
5. Add appropriate labels to your pull request

### Review Process

1. Submit your pull request to the `main` branch
2. One or more maintainers will review your changes
3. Address any feedback or requested changes
4. Once approved, your changes will be merged

### Code Review Guidelines

Reviewers will consider:

- Code quality and style adherence
- Correctness and test coverage
- Performance implications
- Impact on existing functionality
- Documentation completeness

## Architecture and Design Guidelines

### Rompy Architecture

Rompy follows a modular architecture with clear separation of concerns:

- **Configuration**: Model definitions using Pydantic models
- **Execution**: Backend-agnostic execution through backend plugins
- **Data**: Flexible data handling through source and data objects
- **Results**: Post-processing and output handling

### Extending Rompy

To add new functionality:

1. **New Model Types**: Use the plugin system with the `rompy.config` entry point
2. **New Data Sources**: Extend from `SourceBase` classes
3. **New Backends**: Implement the backend interface and register with `rompy.run`
4. **New Processors**: Implement the processor interface and register with `rompy.postprocess`

## Getting Help

If you need help with your contribution:

1. Check the existing documentation
2. Search existing issues for similar problems
3. Ask questions in the issue tracker
4. Reach out to the maintainers via GitHub

## Recognition

All contributors are recognized in the [AUTHORS.rst](httpshttps://github.com/rom-py/rompy/blob/main/AUTHORS.rst) file. Contributions of any size are valuable to the project.

## Pull Request Process

1. Create a feature branch
2. Add your changes
3. Add or update tests as appropriate
4. Update documentation
5. Ensure all tests pass
6. Submit a pull request with a clear description
7. Address review feedback
8. Wait for approval and merge