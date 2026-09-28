"""Issue #5 CLI canonical JSON and exit-code tests."""

import json
from datetime import datetime, timezone

from click.testing import CliRunner

from rompy.cli import cli
from unittest.mock import patch

from rompy.core.responses import (
    LocalArtifact,
    ModelRunFailure,
    ModelRunSuccess,
    RunResultSidecar,
    TimingInfo,
    GenerateFailure,
    PersistenceDiagnostic,
    GenerateSuccess,
    NormalizedContext,
)
from rompy.core.result_persistence import write_run_result


def timing():
    now = datetime.now(timezone.utc)
    return TimingInfo(start_time=now, end_time=now)


def write_run(tmp_path, success=True):
    output = tmp_path / "outputs"
    output.mkdir()
    payload_cls = ModelRunSuccess if success else ModelRunFailure
    fields = dict(
        run_id="cli-run",
        backend_used="local",
        output_dir=str(output),
        timing=timing(),
        artifacts=[LocalArtifact(path="waves.nc")],
        expected_outputs=[LocalArtifact(path="waves.nc")],
        missing_outputs=[],
    )
    if not success:
        fields["error"] = "run failed"
    payload = payload_cls(**fields)
    context = NormalizedContext(
        model_type="base", period_start=datetime(2020, 1, 1, tzinfo=timezone.utc),
        period_end=datetime(2020, 1, 2, tzinfo=timezone.utc), period_interval=3600,
        output_dir=str(output), staging_dir=str(tmp_path), config_hash="",
    )
    sidecar = RunResultSidecar(
        run_id="cli-run", staging_dir=str(tmp_path), normalized_context=context,
        status="success" if success else "failed", success=success,
        error=None if success else payload.error, payload=payload,
    )
    write_run_result(tmp_path, sidecar)
    return output


def processor_config(tmp_path):
    config = tmp_path / "processor.yml"
    config.write_text("type: noop\nvalidate_outputs: false\n")
    return config


def json_lines(output):
    start = output.find('{\n  "kind"')
    if start >= 0:
        return [json.loads(output[start:])]
    start = output.rfind('{')
    return [json.loads(output[start:])]


def test_generate_persistence_failure_emits_one_current_json_document(tmp_path):
    config = tmp_path / "config.yml"
    config.write_text("model_type: base\nrun_id: cli-run\n")
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    result = GenerateFailure(
        run_id="cli-run", staging_dir=str(workspace), generated_files=[], error="render failed",
        timing=timing(), persistence_diagnostic=PersistenceDiagnostic(
            sidecar_kind="generate_result", sidecar_path=str(workspace / "generate_result.json"),
            error="disk full", primary_error="render failed",
        ),
    )
    with patch("rompy.cli.ModelRun") as model_class:
        model_class.return_value.generate.return_value = result
        response = CliRunner().invoke(cli, ["generate", str(config), "--json"])
    documents = [json.loads(line) for line in response.output.splitlines() if line.startswith("{")]
    assert response.exit_code == 1
    assert len(documents) == 1
    assert documents[0]["success"] is False
    assert documents[0]["run_id"] == "cli-run"
    assert documents[0]["payload"]["persistence_diagnostic"]["error"] == "disk full"


def test_run_persistence_failure_does_not_emit_stale_success_sidecar(tmp_path):
    config = tmp_path / "config.yml"
    config.write_text("model_type: base\nrun_id: cli-run\n")
    backend_file = tmp_path / "backend.yml"
    backend_file.write_text('type: local\ncommand: "true"\n')
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    stale = {"kind": "run_result", "schema_version": 2, "run_id": "old", "status": "success", "success": True}
    (workspace / "run_result.json").write_text(json.dumps(stale))
    generated = GenerateSuccess(run_id="cli-run", staging_dir=str(workspace), generated_files=[], timing=timing())
    failed = ModelRunFailure(
        run_id="cli-run", backend_used="local", output_dir=str(workspace), workspace_dir=str(workspace),
        error="primary run failure", timing=timing(), artifacts=[], expected_outputs=[], missing_outputs=[],
        persistence_diagnostic=PersistenceDiagnostic(
            sidecar_kind="run_result", sidecar_path=str(workspace / "run_result.json"),
            error="disk full", primary_error="primary run failure",
        ),
    )
    with patch("rompy.cli.ModelRun") as model_class:
        instance = model_class.return_value
        instance.run_id = "cli-run"
        instance.staging_dir = workspace
        instance.generate.return_value = generated
        instance.run.return_value = failed
        response = CliRunner().invoke(cli, ["run", str(config), "--backend-config", str(backend_file), "--json"])
    documents = [json.loads(line) for line in response.output.splitlines() if line.startswith("{")]
    assert response.exit_code == 1
    assert len(documents) == 1
    assert documents[0].get("run_id") == "cli-run", (response.output, documents[0])
    assert documents[0]["error"] == "primary run failure"
    assert documents[0]["payload"]["persistence_diagnostic"]["error"] == "disk full"


def test_run_generation_persistence_failure_emits_current_generate_failure_once(tmp_path):
    config = tmp_path / "config.yml"
    config.write_text("model_type: base\nrun_id: cli-run\n")
    backend_file = tmp_path / "backend.yml"
    backend_file.write_text('type: local\ncommand: "true"\n')
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    stale = {"kind": "generate_result", "schema_version": 2, "run_id": "old", "status": "success", "success": True}
    (workspace / "generate_result.json").write_text(json.dumps(stale))
    failed = GenerateFailure(
        run_id="cli-run", staging_dir=str(workspace), generated_files=[], error="render primary",
        timing=timing(), persistence_diagnostic=PersistenceDiagnostic(
            sidecar_kind="generate_result", sidecar_path=str(workspace / "generate_result.json"),
            error="disk full", primary_error="render primary",
        ),
    )
    with patch("rompy.cli.ModelRun") as model_class:
        instance = model_class.return_value
        instance.generate.return_value = failed
        response = CliRunner().invoke(
            cli, ["run", str(config), "--backend-config", str(backend_file), "--json"]
        )
    documents = [json.loads(line) for line in response.output.splitlines() if line.startswith("{")]
    assert response.exit_code == 1
    assert len(documents) == 1
    assert documents[0]["kind"] == "generate_result"
    assert documents[0]["run_id"] == "cli-run"
    assert documents[0]["error"] == "render primary"
    assert documents[0]["payload"]["persistence_diagnostic"]["error"] == "disk full"
    assert documents[0]["run_id"] != "old"


def test_postprocess_json_success_is_canonical_and_exits_zero(tmp_path):
    write_run(tmp_path)
    result = CliRunner().invoke(cli, ["postprocess", str(tmp_path), "--processor-config", str(processor_config(tmp_path)), "--json"])
    assert result.exit_code == 0, result.output
    payload = json.loads((tmp_path / "postprocess_result.json").read_text())
    assert payload["kind"] == "postprocess_result"
    assert payload["schema_version"] == 2
    assert payload["success"] is True


def test_postprocess_failed_run_has_canonical_json_and_nonzero_exit(tmp_path):
    write_run(tmp_path, success=False)
    result = CliRunner().invoke(cli, ["postprocess", str(tmp_path), "--processor-config", str(processor_config(tmp_path)), "--json"])
    assert result.exit_code == 1
    payload = json_lines(result.output)[-1]
    assert payload["success"] is False
    assert "success=false" in payload["error"]


def test_postprocess_json_missing_sidecar_is_failure(tmp_path):
    result = CliRunner().invoke(cli, ["postprocess", str(tmp_path), "--processor-config", str(processor_config(tmp_path)), "--json"])
    assert result.exit_code == 1
    payload = json_lines(result.output)[-1]
    assert payload["success"] is False
    assert "Run result sidecar not found" in payload["error"]
