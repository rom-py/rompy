#-----------------------------------------------------------------------------
# Copyright (c) 2020 - 2021, CSIRO 
#
# All rights reserved.
#
# The full license is in the LICENSE file, distributed with this software.
#-----------------------------------------------------------------------------

import logging
import warnings
logger = logging.getLogger('rompy')

import os
import intake

here = os.path.abspath(os.path.dirname(__file__))
cat = intake.open_catalog(os.path.join(here, 'catalogs', 'master.yaml'))

from ._version import get_versions
__version__ = get_versions()['version']
del get_versions
