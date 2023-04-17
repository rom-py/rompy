import os
from datetime import datetime

import pytest
from utils import compare_files

from rompy import TEMPLATES_DIR
from rompy.core import BaseConfig

here = os.path.dirname(os.path.abspath(__file__))


@pytest.fixture
def template():
    return BaseConfig(
        template="../rompy/templates/base",
    )


def test_template():
    config = BaseConfig()
    assert config.template == os.path.join(TEMPLATES_DIR, "base")
