from __future__ import annotations

import inspect
import json
import logging
import os
import platform
from datetime import datetime
from typing import Optional

import cookiecutter.config as cc_config
import cookiecutter.generate as cc_generate
import cookiecutter.repository as cc_repository
from pydantic import BaseModel, PrivateAttr, validator

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
    checkout : str
        The git checkout branch, tag or commit
    template : str
        The template directory
    _datefmt : str
        The date format to be rendered in the template
    """

    run_id: str = "run_id"
    compute_start: datetime = datetime(2020, 2, 21, 4)
    compute_interval: str = "0.25 HR"
    compute_stop: datetime = datetime(2020, 2, 24, 4)
    output_dir: str = "template_output"
    checkout: str = "main"
    template: str | None = None
    _datefmt: str = "%Y%m%d.%H%M%S"
    _generated_at: str = PrivateAttr()
    _generated_on: str = PrivateAttr()
    _generated_by: str = PrivateAttr()

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
            f.write(json.dumps(d, default=json_serial_local, indent=4))

    def generate(self, output_dir: str = None) -> str:
        """Generate the template

        Parameters
        ----------
        output_dir : str, optional

        Returns
        -------
        staging_dir : str
        """
        self._generated_at = str(datetime.utcnow())
        self._generated_by = os.environ.get("USER")
        self._generated_on = platform.node()

        config_dict = cc_config.get_user_config(
            config_file=None,
            default_config=False,
        )

        template = self.template or os.path.dirname(inspect.getmodule(self).__file__)

        repo_dir, cleanup = cc_repository.determine_repo_dir(
            template=template,
            abbreviations=config_dict["abbreviations"],
            clone_to_dir=config_dict["cookiecutters_dir"],
            checkout=self.checkout,
            no_input=True,
        )

        self._write_template_json(repo_dir)

        # regenerate the context so that is is correctly templated
        context = cc_generate.generate_context(
            context_file=os.path.join(repo_dir, "cookiecutter.json"),
        )

        staging_dir = cc_generate.generate_files(
            repo_dir=repo_dir,
            context=context,
            overwrite_if_exists=True,
            output_dir=self.output_dir,
        )
        logger.info(f"Successfully generated project in {output_dir}")
        return staging_dir
