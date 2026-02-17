# -----------------------------------------------------------------------------
# Copyright (c) 2020 - 2021, CSIRO
#
# All rights reserved.
#
# The full license is in the LICENSE file, distributed with this software.
# -----------------------------------------------------------------------------

import warnings
from pathlib import Path

# Import the new logging system
# Use absolute imports for documentation execution
try:
    from .logging import LogFormat, LoggingConfig, LogLevel, get_logger
except (ImportError, ValueError):
    # Fallback for documentation execution context
    try:
        from rompy.logging import LogFormat, LoggingConfig, LogLevel, get_logger
    except ImportError:
        # Create mock objects for documentation purposes
        class LogFormat:
            pass

        class LoggingConfig:
            def configure_logging(self):
                pass

        class LogLevel:
            pass

        def get_logger(name):
            import logging

            return logging.getLogger(name)


# Initialize the logger with default configuration
logger = get_logger(__name__)

# Configure default logging if not already configured
LoggingConfig().configure_logging()

# Configure warnings to be less intrusive
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")
warnings.filterwarnings("ignore", category=UserWarning, module="intake.readers.readers")
warnings.filterwarnings(
    "ignore", message="A custom validator is returning a value other than `self`"
)

# __version__ = _version.get_versions()["version"]
__version__ = "0.6.2"

# Import and re-export formatting utilities
from .formatting import get_formatted_box, get_formatted_header_footer

# Import logging configuration
from .logging import LoggingConfig

# Root directory and templates directory paths
ROOT_DIR = Path(__file__).parent.resolve()
TEMPLATES_DIR = ROOT_DIR / "templates"
