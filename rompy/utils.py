#-----------------------------------------------------------------------------
# Copyright (c) 2020 - 2021, CSIRO 
#
# All rights reserved.
#
# The full license is in the LICENSE file, distributed with this software.
#-----------------------------------------------------------------------------

import numpy as np
import xarray as xr
import logging

logger = logging.getLogger("rompy.util")

def dict_product(d):
    from itertools import product
    keys = d.keys()
    for element in product(*d.values()):
        yield dict(zip(keys, element))
