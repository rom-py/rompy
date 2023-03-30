import os

import pytest
from utils import compare_files

from rompy.core import BaseModel
from rompy.templates.base.model import Template

here = os.path.dirname(os.path.abspath(__file__))


@pytest.fixture
def model():
    return BaseModel(
        run_id="test_base",
        output_dir=os.path.join(here, "simulations"),
        template=Template(),
    )


# test generate method
def test_generate(model):
    model.generate()
    compare_files(
        os.path.join(here, "simulations/test_base/INPUT"),
        os.path.join(here, "simulations/test_base_ref/INPUT"),
    )
