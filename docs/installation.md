# Installation

This guide provides instructions for installing Rompy for different use cases.

## Prerequisites

Before installing Rompy, ensure you have:

- Python 3.10 or higher
- pip package manager
- Git (for installation from source)

### System-specific Requirements

#### Linux/macOS
- Standard Unix-like environment with bash shell
- Development tools (gcc, make) for building C extensions

#### Windows
- Windows 10 or higher
- Windows Subsystem for Linux (WSL) recommended for full functionality
- Visual Studio Build Tools or equivalent for building C extensions

## Installation Scenarios

### Basic Installation

For basic usage and to try out the library:

```bash
pip install rompy
```

### Development Installation

For contributing to the project or modifying the code:

```bash
git clone git@github.com:rom-py/rompy.git
cd rompy
pip install -e .[dev]
```

This installs Rompy in editable mode along with development dependencies.

### Production Installation

For production deployments:

```bash
pip install rompy==0.6.1  # Replace with the specific version you need
```

## Optional Dependencies

Rompy includes several optional dependencies for specific functionality:

- `extra`: Additional dependencies for cloud storage (gcsfs, zarr, cloudpathlib)
- `test`: Dependencies for running tests (pytest, envyaml, coverage)
- `dev`: Development dependencies (pytest, ruff, black)
- `docs`: Dependencies for building documentation (mkdocs, mkdocstrings)

Install with optional dependencies:

```bash
pip install rompy[extra,test]
```

## Virtual Environment (Recommended)

We strongly recommend using a virtual environment:

```bash
# Create a virtual environment
python -m venv rompy_env

# Activate the environment
# On Linux/macOS:
source rompy_env/bin/activate
# On Windows:
rompy_env\Scripts\activate

# Install Rompy
pip install rompy
```

## Troubleshooting

### Installation Issues

If you encounter issues during installation:

1. **Permission errors**: Use a virtual environment or install with the `--user` flag:
   ```bash
   pip install --user rompy
   ```

2. **Dependency conflicts**: Create a fresh virtual environment for Rompy:
   ```bash
   python -m venv fresh_rompy_env
   source fresh_rompy_env/bin/activate  # or appropriate activation command
   pip install rompy
   ```

3. **Compilation errors**: Ensure you have the required system dependencies:
   - Linux: gcc, g++, make, python3-dev
   - macOS: Xcode command line tools
   - Windows: Visual Studio Build Tools

### Upgrade Existing Installation

To upgrade to the latest version:

```bash
pip install --upgrade rompy
```

### Verification

To verify your installation, try importing Rompy:

```python
import rompy
print(f"Rompy version: {rompy.__version__}")
```

## Next Steps

- Go to the [Quickstart Guide](quickstart.md) to begin using Rompy
- Check the [Examples](examples.md) for practical use cases
- Review the [Core Concepts](core_concepts.md) to understand the architecture
