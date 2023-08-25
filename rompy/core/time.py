from datetime import datetime, timedelta
from typing import Any, Optional, Union

from pydantic import field_validator, model_validator, ConfigDict, BaseModel, Field


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


class TimeRange(BaseModel):
    """
    A time range object

    Examples
    --------
    >>> from rompy import TimeRange
    >>> tr = TimeRange(start="2020-01-01", end="2020-01-02")
    >>> tr
    TimeRange(start=datetime.datetime(2020, 1, 1, 0, 0), end=datetime.datetime(2020, 1, 2, 0, 0), duration=None, interval=None, include_end=True)
    >>> tr = TimeRange(start="2020-01-01", duration="1d")
    >>> tr
    TimeRange(start=datetime.datetime(2020, 1, 1, 0, 0), end=datetime.datetime(2020, 1, 2, 0, 0), duration=timedelta(days=1), interval=None, include_end=True)
    >>> tr = TimeRange(start="2020-01-01", duration="1d", interval="1h")
    >>> tr
    TimeRange(start=datetime.datetime(2020, 1, 1, 0, 0), end=None, duration=timedelta(days=1), interval=timedelta(hours=1), include_end=True)
    """

    start: Optional[datetime] = Field(
        None,
        description="The start date of the time range",
        examples=["2020-01-01"],
    )
    end: Optional[datetime] = Field(
        None,
        description="The end date of the time range",
        examples=["2020-01-02"],
    )
    duration: Optional[Union[str, timedelta]] = Field(
        None,
        description="The duration of the time range",
        examples=["1d"],
    )
    interval: Optional[Union[str, timedelta]] = Field(
        "1h",
        description="The frequency of the time range",
        examples=["1h", "'1h'"],
    )
    include_end: bool = Field(
        True,
        description="Determines if the end date should be included in the range",
    )
    model_config = ConfigDict(validate_default=True)

    @field_validator("interval", "duration", mode="before")
    @classmethod
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

    @field_validator("start", "end", mode="before")
    @classmethod
    def validate_start_end(cls, v):
        if v == None:
            return v
        if isinstance(v, datetime):
            return v
        for fmt in [
            "%Y%m%d",
            "%Y%m%dT%H",
            "%Y%m%dT%H%M",
            "%Y%m%dT%H%M%S",
            "%Y%m%d.%H",
            "%Y%m%d.%H%M",
            "%Y%m%d.%H%M%S",
            "%Y-%m-%d",
            "%Y-%m-%dT%H",
            "%Y-%m-%dT%H%M",
        ]:
            try:
                ret = datetime.strptime(v, fmt)
                return ret
            except ValueError:
                pass
        return v

    @model_validator(mode="before")
    @classmethod
    def validate_start_end_duration(cls, data: Any) -> Any:
        if data.get("start") is not None:
            if all(data.get(key) is None for key in ["end", "duration"]):
                raise ValueError("start provided, must provide either end or duration")
        if data.get("end") is not None:
            if all(data.get(key) is None for key in ["start", "duration"]):
                raise ValueError("end provided, must provide either start or duration")
        if data.get("duration") is not None:
            if all(data.get(key) is None for key in ["start", "end"]):
                raise ValueError("duration provided, must provide either start or end")
        if all(data.get(key) is None for key in ["start", "end", "duration"]):
            raise ValueError("Must provide two of start, end, duration")
        if all(data.get(key) is not None for key in ["start", "end", "duration"]):
            raise ValueError("Must provide only two of start, end, duration")
        return data

    @model_validator(mode="after")
    def parse_start_end_duration(self) -> 'TimeRange':
        if self.start is not None and self.end is not None:
            self.duration = self.end - self.start
        if self.start is not None and self.duration is not None:
            self.end = self.start + self.duration
        if self.end is not None and self.duration is not None:
            self.start = self.end - self.duration
        return self

    @property
    def date_range(self) -> list[datetime]:
        start = self.start
        end = self.end
        date_range = []
        while start < end:
            date_range.append(start)
            start += self.interval
            if start + self.interval > end:
                if self.include_end:
                    date_range.append(end)
                break
        return date_range

    def contains(self, date: datetime) -> bool:
        return self.start <= date <= self.end

    def contains_range(self, date_range: "TimeRange") -> bool:
        return self.contains(date_range.start) and self.contains(date_range.end)

    def common_times(self, date_range: "TimeRange") -> list[datetime]:
        common_times = []
        for date in self.date_range:
            if date_range.contains(date):
                common_times.append(date)
        return common_times

    def __str__(self):
        ret = f"\n\tStart: {self.start}\n"
        ret += f"\tEnd: {self.end}\n"
        ret += f"\tDuration: {self.duration}\n"
        ret += f"\tInterval: {self.interval}\n"
        ret += f"\tInclude End: {self.include_end}\n"
        return ret
