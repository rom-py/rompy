from datetime import datetime, tzinfo

import pytest
from dateutil import tz

from rompy.templates.base.model import Template


# write tests for Template class
def test_template():
    template = Template()
    assert template.run_id == "run_id"
    assert template.compute_start == datetime(2020, 2, 21, 4)
    assert template.compute_interval == "0.25 HR"
    assert template.compute_stop == datetime(2020, 2, 24, 4)
    assert template._template == "../templates/base"


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
