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
    compute_start: datetime = datetime(2020, 2, 21, 4)
    compute_interval: str = "0.25 HR"
    compute_stop: datetime = datetime(2020, 2, 24, 4)
    output_dir: str = "simulations"
    config: BaseConfig = BaseConfig()
    _model: str | None = None

    class Config:
        underscore_attrs_are_private = True

    @validator("compute_start", "compute_stop", pre=True)
    def validate_compute_start_stop(cls, v):
        if isinstance(v, datetime):
            return v
        for fmt in [
            "%Y%m%d.%H%M%S",
            "%Y%m%d.%H%M",
            "%Y%m%dT%H%M%S",
            "%Y%m%dT%H%M",
            "%Y%m%dT%H",
            "%Y%m%dT",
            "%Y-%m-%dT%H%M",
            "%Y-%m-%dT%H",
            "%Y-%m-%dT",
        ]:
            try:
                ret = datetime.strptime(v, fmt)
                return ret
            except ValueError:
                pass
        return v

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

    @classmethod
    def load_settings(fn):
        """Load the run settings from a file"""
        with open(fn) as f:
            defaults = json.load(f)

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
        logger.info(f"Template used to generate model: {self.config.template}")

        config_dict = cc_config.get_user_config(
            config_file=None,
            default_config=False,
        )

        repo_dir, cleanup = cc_repository.determine_repo_dir(
            template=self.config.template,
            abbreviations=config_dict["abbreviations"],
            clone_to_dir=config_dict["cookiecutters_dir"],
            checkout=self.config.checkout,
            no_input=True,
        )

        cc_full = {}
        cc_full["cookiecutter"] = self.dict()
        cc_full["cookiecutter"].update(self.config.dict())
        cc_full["cookiecutter"].update({"_template": repo_dir})
        cc_full["cookiecutter"].update({"_generated_at": str(datetime.utcnow())})
        cc_full["cookiecutter"].update({"_generated_by": os.environ.get("USER")})
        cc_full["cookiecutter"].update({"_generated_on": platform.node()})
        cc_full["cookiecutter"].update({"_datefmt": self.config._datefmt})

        staging_dir = cc_generate.generate_files(
            repo_dir=repo_dir,
            context=cc_full,
            overwrite_if_exists=True,
            output_dir=self.output_dir,
        )
        logger.info("")
        logger.info(f"Successfully generated project in {self.output_dir}")
        logger.info(f"Settings saved to {self.save_settings()}")
        logger.info("-----------------------------------------------------")
        return staging_dir

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
