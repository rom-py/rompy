import logging
from pathlib import Path
from typing import Literal, Optional

from pydantic import Field

from .types import RompyBaseModel

logger = logging.getLogger(__name__)


DEFAULT_TEMPLATE = str(Path(__file__).parent.parent / "templates" / "base")


class BaseConfig(RompyBaseModel):
    """Base class for model templates.

    The template class provides the object that is used to set up the model configuration.
    When implemented for a given model, can move along a scale of complexity
    to suit the application.

    In its most basic form, as implemented in this base object, it consists of path to a cookiecutter template
    with the class providing the context for the {{config}} values in that template. Note that any
    {{runtime}} values are filled from the ModelRun object.

    If the template is a git repo, the checkout parameter can be used to specify a branch or tag and it
    will be cloned and used.

    If the object is callable, it will be colled prior to rendering the template. This mechanism can be
    used to perform tasks such as fetching exteral data, or providing additional context to the template
    beyond the arguments provided by the user..
    """

    model_type: Literal["base"] = "base"
    template: Optional[str] = Field(
        description="The path to the model template",
        default=DEFAULT_TEMPLATE,
    )
    checkout: Optional[str] = Field(
        description="The git branch to use if the template is a git repo",
        default="main",
    )

    # noop call for config objects
    def __call__(self, *args, **kwargs):
        return self

    def render(self, context: dict, output_dir: Path | str):
        """Render the configuration template to the output directory.

        This method orchestrates the template rendering process. The default implementation
        uses cookiecutter rendering with the template and checkout defined on this config.
        Subclasses can override this method to implement alternative rendering strategies
        (e.g., direct file writing, Jinja2, custom logic).

        Args:
            context: Full context dictionary. Expected to contain at least 'runtime' and 'config' keys.
            output_dir: Target directory for rendered output.

        Returns:
            str: Path to the staging directory (workspace) containing rendered files.
        """
        # Import locally to avoid potential circular imports at module import time
        from rompy.core.render import render as cookiecutter_render

        cookiecutter_render(context, self.template, output_dir, self.checkout)
