import os
from datetime import datetime

import pytest
from utils import compare_files

from rompy.templates.base.model import Template

here = os.path.dirname(os.path.abspath(__file__))


@pytest.fixture
def template():
    return Template(
        run_id="test_base",
        _template="../rompy/templates/base",
        output_dir=os.path.join(here, "template_output"),
    )


# write tests for Template class
def test_template():
    template = Template()
    assert template.run_id == "run_id"
    assert template.compute_start == datetime(2020, 2, 21, 4)
    assert template.compute_interval == "0.25 HR"
    assert template.compute_stop == datetime(2020, 2, 24, 4)
    assert template._template == ""


def test_datetime_parse():
    compute_stop = datetime(2022, 2, 21, 4)
    for format in [
        "%Y%m%d.%H%M%S",
        "%Y%m%d.%H%M",
        "%Y%m%dT%H%M%S",
        "%Y%m%dT%H%M",
    ]:
        template = Template(compute_stop=compute_stop.strftime(format))
        for period in ["year", "month", "day", "hour"]:
            assert getattr(template.compute_stop, period) == getattr(
                compute_stop, period
            )


def test_datetime_parse_fail():
    compute_stop = datetime(2022, 2, 21, 4)
    for format in [
        "%Y%m%d.%Hhello",
        "%Y%m%dhello",
    ]:
        try:
            template = Template(compute_stop=compute_stop.strftime(format))
        except ValueError:
            pass
        else:
            raise ValueError("Should not be able to parse {format}")


# test generate
def test_generate(template):
    template.generate()
    compare_files(
        os.path.join(here, "template_output/test_base/INPUT"),
        os.path.join(here, "simulations/test_base_ref/INPUT"),
    )
