import os
from datetime import datetime

import pytest
from utils import compare_files

from rompy import TEMPLATES_DIR
from rompy.templates.base.model import Template

here = os.path.dirname(os.path.abspath(__file__))


@pytest.fixture
def template():
    return Template(
        template="../rompy/templates/base",
    )


def test_template():
    template = Template()
    assert template.template == os.path.join(TEMPLATES_DIR, "base")
