from datetime import datetime, timedelta
from typing import List, Optional, Union

from dateutil.relativedelta import relativedelta
from pydantic import root_validator, validator

from .types import RompyBaseModel

time_units = {
    "h": "hours",
    "d": "days",
    "w": "weeks",
    "m": "minutes",
    "s": "seconds",
    "y": "years",
    "H": "hours",
    "D": "days",
    "W": "weeks",
    "M": "minutes",
    "S": "seconds",
    "Y": "years",
}


class DateTimeRange(RompyBaseModel):
    """A time range object

    Parameters
    ----------
    start_date : datetime
        The start date of the time range
    end_date : datetime
        The end date of the time range
    duration : str, timedelta
        The duration of the time range
    frequency : str, timedelta
        The frequency of the time range
    include_end : bool

    Examples
    --------
    >>> from rompy import DateTimeRange
    >>> DateTimeRange(start_date="2020-01-01", end_date="2020-01-02")
    DateTimeRange(start_date=datetime.datetime(2020, 1, 1, 0, 0), end_date=datetime.datetime(2020, 1, 2, 0, 0), duration=None, frequency=None)
    >>> DateTimeRange(start_date="2020-01-01", duration="1d")
    DateTimeRange(start_date=datetime.datetime(2020, 1, 1, 0, 0), end_date=datetime.datetime(2020, 1, 2, 0, 0), duration=datetime.timedelta(days=1), frequency=None)
    >>> DateTimeRange(start_date="2020-01-01", duration="1d", frequency="1h")
    """

    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    duration: Optional[Union[str, timedelta]] = None
    frequency: Optional[Union[str, timedelta]] = "1h"
    include_end: bool = True

    class Config:
        validate_all = True

    @validator("frequency", "duration")
    def valid_duration_interval(cls, v):
        if v == None:
            return v
        if isinstance(v, timedelta):
            return v
        elif isinstance(v, str):
            if v[-1] not in time_units:
                raise ValueError(
                    "Invalid duration unit. Must be one of: h, m, s, d, w, y"
                )
            time_delta_unit = v[-1]
            time_delta_value = int(v[:-1])
            return timedelta(**{time_units[time_delta_unit]: time_delta_value})

    @validator("start_date", "end_date", pre=True)
    def validate_start_end(cls, v):
        if v == None:
            return v
        if isinstance(v, datetime):
            return v
        for fmt in [
            "%Y%m%d.%H%M%S",
            "%Y%m%d.%H%M",
            "%Y%m%dT%H%M%S",
            "%Y%m%dT%H%M",
            "%Y%m%dT%H",
            "%Y%m%dT",
            "%Y-%m-%dT%H%M",
            "%Y-%m-%dT%H",
            "%Y-%m-%d",
        ]:
            try:
                ret = datetime.strptime(v, fmt)
                return ret
            except ValueError:
                pass
        return v

    @root_validator
    def validate_start_end_duration(cls, values):
        # check two out of start_date, end_date, duration are provided
        if values.get("start_date"):
            if not values.get("end_date") and not values.get("duration"):
                raise ValueError(
                    "start_date provided, must provide either end_date or duration"
                )
        if values.get("end_date"):
            if not values.get("start_date") and not values.get("duration"):
                raise ValueError(
                    "end_date provided, must provide either start_date or duration"
                )
        if values.get("duration"):
            if not values.get("start_date") and not values.get("end_date"):
                raise ValueError(
                    "duration provided, must provide either start_date or end_date"
                )
        if (
            values.get("start_date") is None
            and values.get("end_date") is None
            and values.get("duration") is None
        ):
            raise ValueError("Must provide two of start_date, end_date, duration")
        if (
            values.get("start_date") is not None
            and values.get("end_date") is not None
            and values.get("duration") is not None
        ):
            raise ValueError("Must provide only two of start_date, end_date, duration")
        if values.get("start_date") is not None and values.get("end_date") is not None:
            values["duration"] = str(values["end_date"] - values["start_date"])
        if values.get("start_date") is not None and values.get("duration") is not None:
            values["end_date"] = values["start_date"] + values["duration"]
        if values.get("end_date") is not None and values.get("duration") is not None:
            values["start_date"] = values["end_date"] - values["duration"]
        return values

    @property
    def date_range(self) -> List[datetime]:
        start = self.start_date
        end = self.end_date
        date_range = []
        while start < end:
            date_range.append(start)
            start += self.frequency
            if start + self.frequency > end:
                if self.include_end:
                    date_range.append(end)
                break
        return date_range

    def contains(self, date: datetime) -> bool:
        return self.start_date <= date <= self.end_date

    def contains_range(self, date_range: "DateTimeRange") -> bool:
        return self.contains(date_range.start_date) and self.contains(
            date_range.end_date
        )

    def common_times(self, date_range: "DateTimeRange") -> List[datetime]:
        common_times = []
        for date in self.date_range:
            if date_range.contains(date):
                common_times.append(date)
        return common_times
