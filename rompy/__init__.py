# -----------------------------------------------------------------------------
# Copyright (c) 2020 - 2021, CSIRO
#
# All rights reserved.
#
# The full license is in the LICENSE file, distributed with this software.
# -----------------------------------------------------------------------------

import logging
from pathlib import Path

# from . import _version

logger = logging.getLogger("rompy")

installed = []
try:
    from rompy.core import BaseConfig

    installed.append("base")
except ImportError:
    pass
try:
    from rompy.swan import SwanConfig

    installed.append("swan")
except ImportError:
    pass

try:
    from rompy.schism import SchismCSIROConfig

    installed.append("schism")
except ImportError:
    pass

# __version__ = _version.get_versions()["version"]
__version__ = "0.1.0"

ROOT_DIR = Path(__file__).parent.resolve()
TEMPLATES_DIR = ROOT_DIR / "templates"
