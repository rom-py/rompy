from datetime import datetime, timedelta

import pytest

from rompy.core import DateTimeRange


@pytest.fixture
def dtr_hourly():
    return DateTimeRange(end_date="2019-01-02", duration="1d")


@pytest.fixture
def dtr_daily():
    return DateTimeRange(start_date="2019-01-01", duration="3d", frequency="1d")


def test_dtr(dtr_hourly):
    assert dtr_hourly.start_date == datetime(2019, 1, 1)
    assert dtr_hourly.end_date == datetime(2019, 1, 2)
    assert dtr_hourly.duration == timedelta(days=1)
    assert dtr_hourly.frequency == timedelta(hours=1)


def test_bad_args():
    with pytest.raises(ValueError):
        t = DateTimeRange(start_date="2019-01-01")
    with pytest.raises(ValueError):
        t = DateTimeRange(end_date="2019-01-01")
    with pytest.raises(ValueError):
        t = DateTimeRange(start_date="2019-01-01", end_date="2019-01-01", duration="1d")
    with pytest.raises(ValueError):
        t = DateTimeRange()


def test_date_range_hourly(dtr_hourly):
    assert dtr_hourly.date_range[0] == datetime(2019, 1, 1)
    assert dtr_hourly.date_range[-1] == datetime(2019, 1, 2)
    assert len(dtr_hourly.date_range) == 25


def test_date_range_daily(dtr_daily):
    dtr_daily = DateTimeRange(start_date="2019-01-01", duration="3d", frequency="1d")
    assert dtr_daily.date_range[0] == datetime(2019, 1, 1)
    assert dtr_daily.date_range[-1] == datetime(2019, 1, 4)
    assert len(dtr_daily.date_range) == 4
    dtr_daily = DateTimeRange(
        start_date="2019-01-01", duration="3d", frequency="1d", include_end=False
    )
    assert dtr_daily.date_range[0] == datetime(2019, 1, 1)
    assert dtr_daily.date_range[-1] == datetime(2019, 1, 3)
    assert len(dtr_daily.date_range) == 3
