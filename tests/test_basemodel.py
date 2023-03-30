import pytest
from utils import compare_files

from rompy.core import BaseModel
from rompy.templates.base.model import Template


@pytest.fixture
def model():
    return BaseModel(run_id="test_base", output_dir="simulations", template=Template())


# test generate method
def test_generate(model):
    model.generate()
    compare_files("simulations/test_base/INPUT", "simulations/test_base_ref/INPUT")
