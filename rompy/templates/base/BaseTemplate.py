from __future__ import annotations

from pydantic import BaseModel


class BaseTemplate(BaseModel):
    run_id: str
    compute_start: str
    compute_interval: str
    compute_stop: str
    _generated_at: str
    _generated_on: str
    _generated_by: str
    _template: str
