import logging

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

    arg1: str = "foo"
    arg2: str = "bar"

    def __call__(self, runtime):
        return self.dict()
