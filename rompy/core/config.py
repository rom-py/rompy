import logging

from typing_extensions import Literal

from .types import RompyBaseModel

logger = logging.getLogger(__name__)


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

    class Config:
        extra = "allow"
