from __future__ import annotations

import inspect
import json
import logging
import os
from datetime import datetime
from typing import Optional

import cookiecutter.config as cc_config
import cookiecutter.generate as cc_generate
import cookiecutter.repository as cc_repository
from pydantic import BaseModel, PrivateAttr, validator

from rompy import TEMPLATES_DIR

logger = logging.getLogger(__name__)


def json_serial(obj, datetimefmt="%Y%m%d.%H%M%S"):
    """JSON serializer for objects not serializable by default json code"""

    if isinstance(obj, datetime):
        return obj.strftime(datetimefmt)
    raise TypeError("Type %s not serializable" % type(obj))


class Template(BaseModel):
    """A base class for all templates

    Parameters
    ----------
    checkout : str
        The git checkout branch, tag or commit
    template : str
        The template directory
    _datefmt : str
        The date format to be rendered in the template
    """

    template: str = os.path.join(TEMPLATES_DIR, "base")
    checkout: str = "main"
    _datefmt: str = "%Y%m%d.%H%M%S"
    _generated_at: str = PrivateAttr()
    _generated_on: str = PrivateAttr()
    _generated_by: str = PrivateAttr()

    def _write_template_json(self, template_dir):
        """Write the cookiecutter.json file from pydantic template

        returns
        -------
        template : str
        """

        def json_serial_local(obj):
            return json_serial(obj, self._datefmt)

        with open(os.path.join(template_dir, "cookiecutter.json"), "w") as f:
            d = self.dict()
            d.update({"_template": template_dir})
            d.update({"_generated_at": self._generated_at})
            d.update({"_generated_by": self._generated_by})
            d.update({"_generated_on": self._generated_on})
            d.update({"_datefmt": self._datefmt})
            f.write(json.dumps(d, default=json_serial_local, indent=4))
