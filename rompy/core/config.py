import logging
from typing import Optional

from pydantic import Field
from typing_extensions import Literal

from .types import RompyBaseModel

logger = logging.getLogger(__name__)


class BaseConfig(RompyBaseModel):
    """A base class for all templates"""

    model_type: Literal["base"] = "base"
    template: Optional[str] = Field(
        description="The path to the model template",
        default="/source/rompy/rompy/templates/base",
    )
    checkout: Optional[str] = Field(
        description="The git branch to use",
        default="main",
    )

    class Config:
        extra = "allow"
