"""
Initialization script for mkdocs-pyscript in Rompy documentation.

This script sets up the Python environment for executable code examples
in the Rompy documentation. It imports necessary modules and potentially
creates mock objects for complex backend operations that can't be executed
in the browser environment.
"""

# Import common Rompy modules that users will likely need in examples
try:
    from rompy.model import ModelRun
    from rompy.core.config import BaseConfig
    from rompy.core.time import TimeRange
    from rompy.core.grid import RegularGrid
    from rompy.core.data import DataGrid, DataBoundary
    from rompy.core.source import SourceFile, SourceIntake
    from rompy.backends import LocalConfig
    print("Rompy modules imported successfully")
except ImportError as e:
    print(f"Could not import Rompy modules: {e}")
    # In a browser environment, we might need to handle this differently
    # or provide mock implementations

# For documentation purposes, we might want to create mock implementations
# of certain functions that would normally interact with external systems
def mock_model_run():
    """
    A mock implementation for documentation purposes.
    This would not actually run a model but simulate the behavior for docs.
    """
    pass

# Set up any necessary configuration for the documentation environment
print("Pyscript environment initialized for Rompy documentation")