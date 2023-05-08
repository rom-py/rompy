import os
import shutil
from datetime import datetime

import pytest
from utils import compare_files

from rompy import TEMPLATES_DIR
from rompy.core import BaseConfig, BaseModel, TimeRange

here = os.path.dirname(os.path.abspath(__file__))


@pytest.fixture
def template():
    return BaseConfig(
        template="../rompy/templates/base",
    )


# def test_template():
#     config = BaseConfig()
#     assert config.template == os.path.join(TEMPLATES_DIR, "base")


def test_newbaseconfig():
    """Test the swantemplate function."""
    run_dir = "simulations/test_base"
    config = BaseConfig()
    runtime = BaseModel(run_id="test_base", output_dir="simulations")
    config.write(
        runtime=runtime,
    )
    compare_files(
        os.path.join(here, "simulations/test_base_ref/INPUT"),
        os.path.join(here, run_dir, "INPUT"),
    )
    shutil.rmtree(run_dir)
