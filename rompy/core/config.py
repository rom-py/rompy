import logging
import os
from typing import Optional

from pydantic import Field
from typing_extensions import Literal

from .types import RompyBaseModel

logger = logging.getLogger(__name__)

here = os.path.dirname(os.path.abspath(__file__))


class BaseConfig(RompyBaseModel):
    """A base class for all templates

    Parameters
    ----------
    arg1 : str
        Fictional argument 1
    arg1 : str
        Fictional argument 1
    """

    model_type: Literal["base"] = "base"
    template: Optional[str] = Field(
        description="The path to the model template",
        default="/source/rompy/rompy/templates/base",
        # default=os.path.join(here, "../rompy/templates/swan"),
    )
    checkout: Optional[str] = Field(
        description="The git branch to use",
        default="main",
    )

    class Config:
        extra = "allow"

    def __call__(self, runtime):
        return self.dict()
