from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, PrivateAttr


class Template(BaseModel):
    run_id: str = "run_id"
    compute_start: str = "20200221.040000"
    compute_interval: str = "0.25 HR"
    compute_stop: str = "20200224.040000"
    _template: str = "../templates/base"
    _generated_at: str = PrivateAttr()
    _generated_on: str = PrivateAttr()
    _generated_by: str = PrivateAttr()

    # class Config:
    #     underscore_attrs_are_private = True
