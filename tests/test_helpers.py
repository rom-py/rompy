from typing import Optional, Any

from rompy.core.config import BaseConfig


class DemoConfig(BaseConfig):
    """Demo/Test config used by tests to provide arg1/arg2.

    Intentionally does not change the model_type tag so the ModelRun
    discriminator still recognizes it as a base config.
    """

    arg1: str
    arg2: str
    run: Optional[Any] = None
