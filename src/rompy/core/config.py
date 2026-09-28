import logging
import warnings
from pathlib import Path
from typing import TYPE_CHECKING, List, Literal, Optional

from pydantic import Field

from .types import RompyBaseModel

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from rompy.core.responses import Artifact


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

    def expected_artifacts(self) -> List["Artifact"]:
        """Return the list of artifacts this config expects to produce.

        Override in subclasses to declare expected output files. The base
        implementation always returns an empty list and emits a warning to
        remind plugin authors to implement this method.

        Returns:
            List[Artifact]: Expected artifacts (empty list in base implementation).
        """

        warnings.warn(
            f"{type(self).__name__}.expected_artifacts() is not implemented. "
            "Override this method to declare expected output artifacts.",
            UserWarning,
            stacklevel=2,
        )
        return []

    def validate_outputs(self, output_dir: Path | str) -> List["Artifact"]:
        """Discover and classify output artifacts in output_dir.

        Calls ``expected_artifacts()`` to learn what the config expects, warns
        for each expected artifact that is not found, then falls back to a
        naive ``rglob`` + extension-based classification of all files present.

        Override in subclasses to implement model-specific validation logic.

        Args:
            output_dir: Directory to inspect for output files.

        Returns:
            List[Artifact]: All artifacts found in output_dir.
        """
        from rompy.core.responses import Artifact, ArtifactType  # avoid circularity

        warnings.warn(
            f"{type(self).__name__}.validate_outputs() is not implemented. "
            "Falling back to generic file discovery. Override this method "
            "to perform model-specific output validation.",
            UserWarning,
            stacklevel=2,
        )

        output_dir = Path(output_dir)

        # Check expected artifacts and warn for missing ones
        expected = self.expected_artifacts()
        for artifact in expected:
            artifact_path = Path(artifact.path)
            # Resolve relative paths against output_dir
            if not artifact_path.is_absolute():
                artifact_path = output_dir / artifact_path
            if not artifact_path.exists():
                warnings.warn(
                    f"Expected artifact not found: {artifact.path}",
                    UserWarning,
                    stacklevel=2,
                )

        # Generic discovery: rglob all files and classify by extension
        _EXT_MAP = {
            ".yaml": ArtifactType.YAML,
            ".yml": ArtifactType.YAML,
            ".nc": ArtifactType.NETCDF,
            ".png": ArtifactType.PLOT,
            ".jpg": ArtifactType.PLOT,
            ".jpeg": ArtifactType.PLOT,
            ".pdf": ArtifactType.PLOT,
            ".svg": ArtifactType.PLOT,
            ".txt": ArtifactType.TEXT,
        }

        artifacts = []
        if output_dir.exists():
            for file_path in output_dir.rglob("*"):
                if not file_path.is_file():
                    continue
                suffix = file_path.suffix.lower()
                artifact_type = _EXT_MAP.get(suffix, ArtifactType.OTHER)
                artifacts.append(
                    Artifact(
                        path=file_path.relative_to(output_dir).as_posix(),
                        artifact_type=artifact_type,
                        size_bytes=file_path.stat().st_size,
                    )
                )

        return artifacts
