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

    template: str = os.path.join(TEMPLATES_DIR, "base")
    checkout: str = "main"

    _datefmt: str = "%Y%m%d.%H%M%S"
    _generated_at: str = PrivateAttr()
    _generated_on: str = PrivateAttr()
    _generated_by: str = PrivateAttr()

    def _set_generation_medatadata(self):
        self._generated_at = str(datetime.utcnow())
        self._generated_by = os.environ.get("USER")
        self._generated_on = platform.node()

    def generate(self, runtime: rompy.core.BaseModel) -> str:
        """Generate input file

        Parameters
        ----------
        run_dir : str
            Path to run directory
        """
        self._set_generation_medatadata()
        output = ""
        output += f"$\n"
        output += f"$ BASE - Simple example template used by rompy\n"
        output += f"$ Template: \n"
        output += f"$ Generated: {self._generated_at} on {self._generated_on} by {self._generated_by}\n"
        output += f"$ projection: wgs84\n"
        output += f"$\n"
        output += f"\n"
        output += f"run_id: '{runtime.run_id}'\n"
        output += f"compute_start: {runtime.compute_start.strftime(self._datefmt)}\n"
        output += f"compute_interval: {runtime.compute_interval}\n"
        output += f"compute_stop: {runtime.compute_stop.strftime(self._datefmt)}\n"
        return output

    def write(self, runtime: rompy.core.BaseModel) -> None:
        """Write input file

        Parameters
        ----------
        run_dir : str
            Path to run directory
        """
        outdir = os.path.join(runtime.output_dir, runtime.run_id)
        os.makedirs(outdir, exist_ok=True)
        with open(os.path.join(outdir, "INPUT"), "w") as f:
            f.write(self.generate(runtime=runtime))
