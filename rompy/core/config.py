import logging
from typing import Optional, Literal

from pathlib import Path

from pydantic import Field

from .types import RompyBaseModel


logger = logging.getLogger(__name__)


DEFAULT_TEMPLATE = str(Path(__file__).parent.parent / "templates" / "base")

class BaseConfig(RompyBaseModel):
    """A base class for all templates"""

    model_type: Literal["base"] = "base"
    template: Optional[str] = Field(
        description="The path to the model template",
        default=DEFAULT_TEMPLATE,
    )
    checkout: Optional[str] = Field(
        description="The git branch to use if the template is a git repo",
        default="main",
    )

    class Config:
        extra = "allow"
