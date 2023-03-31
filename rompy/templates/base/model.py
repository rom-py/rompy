from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, PrivateAttr, validator


class Template(BaseModel):
    run_id: str = "run_id"
    # compute_start: str = "20200221.040000"
    compute_start: datetime = datetime(2020, 2, 21, 4)
    compute_interval: str = "0.25 HR"
    # compute_stop: datetime = "20200224.040000"
    compute_stop: datetime = datetime(2020, 2, 24, 4)
    _template: str = "../templates/base"
    _datafmt: str = "%Y%m%d.%H%M%S"
    _generated_at: str = PrivateAttr()
    _generated_on: str = PrivateAttr()
    _generated_by: str = PrivateAttr()

    @validator("compute_start", "compute_stop", pre=True)
    def validate_compute_start_stop(cls, v):
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
            "%Y-%m-%dT",
        ]:
            try:
                ret = datetime.strptime(v, fmt)
                return ret
            except ValueError:
                pass
        return v
