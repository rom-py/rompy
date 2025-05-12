from datetime import datetime
from pathlib import Path

import pytest

from rompy import TEMPLATES_DIR
from rompy.core.config import BaseConfig
from rompy.core.time import TimeRange
from rompy.model import ModelRun

from .utils import compare_files

here = Path(__file__).parent


@pytest.fixture
def template():
    return BaseConfig(
        template="../rompy/templates/base",
    )


# def test_template():
#     config = BaseConfig()
#     assert config.template == os.path.join(TEMPLATES_DIR, "base")


def test_newbaseconfig(tmpdir):
    """Test the swantemplate function."""
    config = BaseConfig(arg1="foo", arg2="bar")
    runtime = ModelRun(
        run_id="test_base",
        output_dir=str(tmpdir),
        config=config,
    )
    runtime.generate()
    compare_files(
        tmpdir / runtime.run_id / "INPUT",
        here / "simulations" / "test_base_ref" / "INPUT",
    )


def test_custom_template(tmpdir):
    config = BaseConfig(arg1="foo", arg2="bar")
    runtime = ModelRun(
        run_id="test_base",
        output_dir=str(tmpdir),
        config=config,
    )
    runtime.generate()
    compare_files(
        here / "simulations" / "test_base_ref" / "INPUT",
        tmpdir / runtime.run_id / "INPUT",
    )
