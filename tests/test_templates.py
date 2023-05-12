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
    run_dir = os.path.join(here, "simulations")
    run_id = "test_base"
    config = BaseConfig()
    runtime = BaseModel(
        run_id=run_id,
        output_dir=run_dir,
    )
    config.write(
        runtime=runtime,
    )
    compare_files(
        os.path.join(here, "simulations/test_base_ref/INPUT"),
        os.path.join(run_dir, run_id, "INPUT"),
    )
    shutil.rmtree(os.path.join(run_dir, run_id))
