from click.testing import CliRunner
from rompy.cli import cli


def test_generate_help_mentions_sidecar_and_json():
    runner = CliRunner()
    result = runner.invoke(cli, ["generate", "--help"])
    assert result.exit_code == 0
    assert "generate_result.json" in result.output
    assert "--json" in result.output


def test_run_help_mentions_sidecar_and_json():
    runner = CliRunner()
    result = runner.invoke(cli, ["run", "--help"])
    assert result.exit_code == 0
    assert "run_result.json" in result.output
    assert "--json" in result.output


def test_postprocess_help_mentions_sidecar_and_json():
    runner = CliRunner()
    result = runner.invoke(cli, ["postprocess", "--help"])
    assert result.exit_code == 0
    assert "run_result.json" in result.output
    assert "postprocess_result.json" in result.output
    assert "STAGING" in result.output
    assert "--force" in result.output
    assert "--json" in result.output
