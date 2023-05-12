from __future__ import annotations

import logging
import os
import platform
from datetime import datetime

from pydantic import PrivateAttr

import rompy
from rompy import TEMPLATES_DIR

from .types import RompyBaseModel

# from rompy.data import DataBlob, DataGrid

logger = logging.getLogger(__name__)


class BaseConfig(RompyBaseModel):
    """A base class for all templates

    Parameters
    ----------
    template : str
        The template directory
    checkout : str
        The git checkout branch, tag or commit. Only used if the template is a git repository
    _datefmt : str
        The date format to be rendered in the template
    """

    arg1: str = "foo"
    arg2: str = "bar"

    def __call__(self):
        return self.dict()
