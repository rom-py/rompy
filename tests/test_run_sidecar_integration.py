"""Integration tests for ModelRun.run() result sidecar persistence."""

import json
from datetime import datetime, timezone

import pytest

from rompy.backends.config import LocalConfig
from rompy.core.responses import (
    GenerateSuccess,
    GenerateResultSidecar,
    NormalizedContext,
    TimingInfo,
)
from rompy.core.result_persistence import write_generate_result
from rompy.model import ModelRun
from tests.test_helpers import DemoConfig


@pytest.mark.integration
def test_model_run_writes_run_result_sidecar(tmp_path):
    """Verify ModelRun.run() writes run_result.json sidecar file on execution."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    model = ModelRun(
        config=DemoConfig(arg1="foo", arg2="bar"),
        run_id="test-run-sidecar",
        output_dir=str(tmp_path / "output"),
    )

    backend = LocalConfig(command="exit 1", timeout=60)

    result = model.run(backend=backend, workspace_dir=str(workspace))

    assert result.success is False

    sidecar_path = workspace / "run_result.json"
    assert sidecar_path.exists(), "run_result.json should be written"

    sidecar_data = json.loads(sidecar_path.read_text())
    assert sidecar_data["kind"] == "run_result"
    assert sidecar_data["schema_version"] == 2
    assert sidecar_data["success"] is False
    assert sidecar_data["run_id"] == "test-run-sidecar"
    assert sidecar_data["staging_dir"] == str(workspace)


@pytest.mark.integration
def test_run_sidecar_copies_normalized_context_from_generate(tmp_path):
    """Verify run() copies normalized_context from generate_result.json if present."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    model = ModelRun(
        config=DemoConfig(arg1="foo", arg2="bar"),
        run_id="test-context-copy",
        output_dir=str(tmp_path / "output"),
    )

    gen_context = NormalizedContext(
        model_type="demo",
        period_start=model.period.start.replace(tzinfo=timezone.utc),
        period_end=model.period.end.replace(tzinfo=timezone.utc),
        period_interval=model.period.interval.total_seconds(),
        output_dir=str(model.output_dir),
        staging_dir=str(workspace),
        config_hash="abc123",
        extensions={"custom_key": "custom_value"},
    )

    gen_sidecar = GenerateResultSidecar(
        created_at=datetime.now(timezone.utc),
        run_id=model.run_id,
        staging_dir=str(workspace),
        status="success",
        success=True,
        normalized_context=gen_context,
        payload=GenerateSuccess(
            staging_dir=str(workspace),
            generated_files=[],
            timing=TimingInfo(
                start_time=datetime.now(timezone.utc), end_time=datetime.now(timezone.utc)
            ),
            run_id=model.run_id,
        ),
    )

    write_generate_result(workspace, gen_sidecar)

    backend = LocalConfig(command="exit 0", timeout=60)

    result = model.run(backend=backend, workspace_dir=str(workspace))

    assert result.success is True

    sidecar_path = workspace / "run_result.json"
    assert sidecar_path.exists()

    sidecar_data = json.loads(sidecar_path.read_text())
    assert "normalized_context" in sidecar_data
    assert sidecar_data["normalized_context"]["model_type"] == "demo"
    assert sidecar_data["normalized_context"]["period_interval"] == model.period.interval.total_seconds()
    assert sidecar_data["normalized_context"]["config_hash"] == "abc123"
    assert (
        sidecar_data["normalized_context"]["extensions"]["custom_key"] == "custom_value"
    )


@pytest.mark.integration
def test_run_sidecar_computes_fallback_normalized_context(tmp_path):
    """Verify run() computes fallback normalized_context when generate_result.json is absent."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    model = ModelRun(
        config=DemoConfig(arg1="foo", arg2="bar"),
        run_id="test-context-fallback",
        output_dir=str(tmp_path / "output"),
    )

    backend = LocalConfig(command="exit 1", timeout=60)

    result = model.run(backend=backend, workspace_dir=str(workspace))

    assert result.success is False

    sidecar_path = workspace / "run_result.json"
    assert sidecar_path.exists()

    sidecar_data = json.loads(sidecar_path.read_text())
    assert "normalized_context" in sidecar_data

    ctx = sidecar_data["normalized_context"]
    assert ctx["model_type"] == "base"
    assert ctx["staging_dir"] == str(workspace)
    assert ctx["output_dir"] == str(tmp_path / "output")
    assert "period_start" in ctx
    assert "period_end" in ctx
    assert ctx["period_interval"] == model.period.interval.total_seconds()
    assert ctx["config_hash"] == ""
    assert ctx["extensions"] == {}
