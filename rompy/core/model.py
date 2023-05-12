import glob
import json
import logging
import os
import platform
import zipfile as zf
from datetime import datetime

import cookiecutter.config as cc_config
import cookiecutter.generate as cc_generate
import cookiecutter.repository as cc_repository
from pydantic import validator

from .config import BaseConfig
from .render import render
from .time import TimeRange
from .types import RompyBaseModel

logger = logging.getLogger(__name__)


class BaseModel(RompyBaseModel):
    """A base class for all models

    Parameters
    ----------

    run_id : str
        The run id
    compute_start : datetime
        The start time of the simulation
    compute_interval : str
        The time interval of the simulation
    compute_stop : datetime
        The stop time of the simulation
    output_dir : str
        The output directory
    config : BaseConfig
        The configuration object
    """

    run_id: str = "run_id"
    period: TimeRange = TimeRange(
        start=datetime(2020, 2, 21, 4),
        end=datetime(2020, 2, 24, 4),
        interval="15M",
    )
    output_dir: str = "simulations"
    config: BaseConfig = BaseConfig()
    template: str = "/source/rompy/rompy/templates/base"
    checkout: str = "main"
    _model: str | None = None
    _datefmt: str = "%Y%m%d.%H%M%S"

    @property
    def staging_dir(self):
        """The directory where the model is staged for execution

        returns
        -------
        staging_dir : str
        """

        return os.path.join(self.output_dir, self.run_id)

    @property
    def grid(self) -> "core.Grid":
        """The grid used by the model

        returns
        -------
        grid : core.Grid
        """
        return self._get_grid()

    def _get_grid(self):
        """Subclasses should return an instance of core.Grid"""
        raise NotImplementedError

    def save_settings(self) -> str:
        """Save the run settings

        returns
        -------
        settingsfile : str
        """
        settingsfile = os.path.join(self.output_dir, f"settings_{self.run_id}.yaml")
        with open(settingsfile, "w") as f:
            f.write(self.yaml())
        return settingsfile

    # def generate(self) -> str:
    #     self.config.generate(self)

    @property
    def _generation_medatadata(self):
        return dict(
            _generated_at=str(datetime.utcnow()),
            _generated_by=os.environ.get("USER"),
            _generated_on=platform.node(),
        )

    def generate(self) -> str:
        """Generate the model input files

        returns
        -------
        staging_dir : str
        """
        logger.info("")
        logger.info("-----------------------------------------------------")
        logger.info("Model settings:")
        print("")
        logger.info(self.yaml(indent=2))
        logger.info(f"Template used to generate model: {self.template}")

        cc_full = {}
        cc_full["runtime"] = self.dict()
        # cc_full["runtime"].update({"_generated_at": str(datetime.utcnow())})
        # cc_full["runtime"].update({"_generated_by": os.environ.get("USER")})
        # cc_full["runtime"].update({"_generated_on": platform.node()})
        cc_full["runtime"].update(self._generation_medatadata)
        cc_full["runtime"].update({"_datefmt": self._datefmt})

        if callable(self.config):
            cc_full["config"] = self.config()
        else:
            cc_full["config"] = self.config

        staging_dir = render(cc_full, self.template, self.checkout, self.output_dir)

        logger.info("")
        logger.info(f"Successfully generated project in {self.output_dir}")
        logger.info(f"Settings saved to {self.save_settings()}")
        logger.info("-----------------------------------------------------")
        return staging_dir

    def write(self):
        self.config.write(self)

    def zip(self) -> str:
        """Zip the input files for the model run

        This function zips the input files for the model run and returns the
        name of the zip file. It also cleans up the staging directory leaving
        only the settings.json file that can be used to repoducte the run.

        returns
        -------
        zip_fn : str
        """

        # Always remove previous zips
        zip_fn = self.staging_dir + "/simulation.zip"
        if os.path.exists(zip_fn):
            os.remove(zip_fn)

        # Zip the input files
        run_files = glob.glob(self.staging_dir + "/**/*", recursive=True)
        with zf.ZipFile(zip_fn, mode="w", compression=zf.ZIP_DEFLATED) as z:
            for f in run_files:
                z.write(f, f.replace(self.staging_dir, ""))  # strip off the path prefix

        # Clean up run files leaving the settings.json
        for f in run_files:
            if not os.path.basename(f) == "settings.json":
                if os.path.isfile(f):
                    os.remove(f)

        # Clean up any directories
        for f in run_files:
            if os.path.isdir(f):
                os.rmdir(f)

        return zip_fn

    def __call__(self):
        return self.generate()

    def __repr__(self):
        return self.yaml()
