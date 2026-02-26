import unittest.mock

from rompy.model import ModelRun
from rompy.core.config import BaseConfig


def test_modelrun_delegates_to_config_render(tmp_path):
    """ModelRun.generate() delegates rendering to config.render()."""

    # Setup
    class TestConfig(BaseConfig):
        def render(self, context: dict, output_dir):
            # real implementation replaced by mock in the test
            return str(tmp_path / "staging")

    config = TestConfig(template="../rompy/templates/base", checkout=None)
    model_run = ModelRun(run_id="test", output_dir=str(tmp_path), config=config)

    # Patch the class method so the instance call is intercepted. Inspect
    # positional args to find the context and output_dir regardless of whether
    # the mock was bound to the instance or the class.
    # Patch by import path to avoid binding issues with Pydantic-generated classes
    with unittest.mock.patch.object(
        TestConfig, "render", return_value=str(tmp_path / "staging")
    ) as mock_render:
        # Execute
        result = model_run.generate()

        # Verify delegation
        mock_render.assert_called_once()
        call_args = mock_render.call_args
        pos_args = call_args[0]

        # Locate the context dict (contains 'runtime') and the output_dir arg
        context_arg = next(
            (a for a in pos_args if isinstance(a, dict) and "runtime" in a), None
        )
        output_dir_arg = next(
            (a for a in pos_args if str(a) == str(model_run.output_dir)), None
        )

        assert isinstance(context_arg, dict)
        assert "runtime" in context_arg
        assert "config" in context_arg
        assert output_dir_arg == model_run.output_dir
        assert result == str(tmp_path / "staging")
