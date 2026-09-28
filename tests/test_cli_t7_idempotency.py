import json
from datetime import datetime, timezone

import pytest
from click.testing import CliRunner

from rompy.cli import cli
from rompy.core.responses import (
    NormalizedContext,
    ModelRunSuccess,
    PostprocessSuccess,
    PostprocessFailure,
    PostprocessResultSidecar,
    RunResultSidecar,
    TimingInfo,
)
from rompy.core.result_persistence import (
    POSTPROCESS_RESULT_FILENAME,
    write_postprocess_result,
    write_run_result,
)
from rompy.model import ModelRun


@pytest.fixture
def cli_runner():
    return CliRunner()


@pytest.fixture
def staging_with_successful_postprocess_result(tmp_path):
    model = ModelRun(
        run_id="test-idempotency",
        output_dir=tmp_path / "output",
        run_id_subdir=True,
    )
    staging_dir = model.staging_dir
    staging_dir.mkdir(parents=True, exist_ok=True)

    timing = TimingInfo(
        start_time=datetime.now(timezone.utc),
        end_time=datetime.now(timezone.utc),
    )

    run_result = ModelRunSuccess(
        success=True,
        run_id="test-idempotency",
        backend_used="LocalBackend",
        output_dir=str(staging_dir),
        timing=timing,
        artifacts=[],
        expected_outputs=[],
        missing_outputs=[],
    )
    normalized = NormalizedContext(
        model_type="modelrun",
        period_start=datetime.now(timezone.utc),
        period_end=datetime.now(timezone.utc),
        period_interval=7200.0,
        output_dir=str(model.output_dir),
        staging_dir=str(staging_dir),
        config_hash="",
        extensions={},
    )
    run_sidecar = RunResultSidecar(
        created_at=datetime.now(timezone.utc),
        run_id="test-idempotency",
        staging_dir=str(staging_dir),
        status="success",
        success=True,
        normalized_context=normalized,
        payload=run_result,
    )
    write_run_result(staging_dir, run_sidecar)

    postprocess_result = PostprocessSuccess(
        success=True,
        run_id="test-idempotency",
        output_dir=str(staging_dir),
        validated=True,
        timing=timing,
        artifacts=[],
        expected_outputs=[],
        missing_outputs=[],
    )
    postprocess_sidecar = PostprocessResultSidecar(
        created_at=datetime.now(timezone.utc),
        run_id="test-idempotency",
        staging_dir=str(staging_dir),
        status="success",
        success=True,
        payload=postprocess_result,
    )
    write_postprocess_result(staging_dir, postprocess_sidecar)

    return staging_dir, model


@pytest.fixture
def staging_with_failed_postprocess_result(tmp_path):
    model = ModelRun(
        run_id="test-idempotency-failed",
        output_dir=tmp_path / "output",
        run_id_subdir=True,
    )
    staging_dir = model.staging_dir
    staging_dir.mkdir(parents=True, exist_ok=True)

    timing = TimingInfo(
        start_time=datetime.now(timezone.utc),
        end_time=datetime.now(timezone.utc),
    )

    run_result = ModelRunSuccess(
        success=True,
        run_id="test-idempotency-failed",
        backend_used="LocalBackend",
        output_dir=str(staging_dir),
        timing=timing,
        artifacts=[],
        expected_outputs=[],
        missing_outputs=[],
    )
    normalized = NormalizedContext(
        model_type="modelrun",
        period_start=datetime.now(timezone.utc),
        period_end=datetime.now(timezone.utc),
        period_interval=7200.0,
        output_dir=str(model.output_dir),
        staging_dir=str(staging_dir),
        config_hash="",
        extensions={},
    )
    run_sidecar = RunResultSidecar(
        created_at=datetime.now(timezone.utc),
        run_id="test-idempotency-failed",
        staging_dir=str(staging_dir),
        status="success",
        success=True,
        normalized_context=normalized,
        payload=run_result,
    )
    write_run_result(staging_dir, run_sidecar)

    postprocess_result = PostprocessFailure(
        success=False,
        run_id="test-idempotency-failed",
        output_dir=str(staging_dir),
        error="Previous processing failed",
        timing=timing,
        artifacts=[],
        expected_outputs=[],
        missing_outputs=[],
    )
    postprocess_sidecar = PostprocessResultSidecar(
        created_at=datetime.now(timezone.utc),
        run_id="test-idempotency-failed",
        staging_dir=str(staging_dir),
        status="failed",
        success=False,
        error="Previous processing failed",
        payload=postprocess_result,
    )
    write_postprocess_result(staging_dir, postprocess_sidecar)

    return staging_dir, model


@pytest.fixture
def staging_with_run_result_only(tmp_path):
    model = ModelRun(
        run_id="test-first-postprocess",
        output_dir=tmp_path / "output",
        run_id_subdir=True,
    )
    staging_dir = model.staging_dir
    staging_dir.mkdir(parents=True, exist_ok=True)

    timing = TimingInfo(
        start_time=datetime.now(timezone.utc),
        end_time=datetime.now(timezone.utc),
    )

    run_result = ModelRunSuccess(
        success=True,
        run_id="test-first-postprocess",
        backend_used="LocalBackend",
        output_dir=str(staging_dir),
        timing=timing,
        artifacts=[],
        expected_outputs=[],
        missing_outputs=[],
    )
    normalized = NormalizedContext(
        model_type="modelrun",
        period_start=datetime.now(timezone.utc),
        period_end=datetime.now(timezone.utc),
        period_interval=7200.0,
        output_dir=str(model.output_dir),
        staging_dir=str(staging_dir),
        config_hash="",
        extensions={},
    )
    run_sidecar = RunResultSidecar(
        created_at=datetime.now(timezone.utc),
        run_id="test-first-postprocess",
        staging_dir=str(staging_dir),
        status="success",
        success=True,
        normalized_context=normalized,
        payload=run_result,
    )
    write_run_result(staging_dir, run_sidecar)

    return staging_dir, model


def test_postprocess_skips_when_already_completed(
    cli_runner, staging_with_successful_postprocess_result, tmp_path
):
    staging_dir, model = staging_with_successful_postprocess_result

    original_sidecar = staging_dir / POSTPROCESS_RESULT_FILENAME
    original_content = original_sidecar.read_text()
    original_data = json.loads(original_content)

    processor_config = tmp_path / "processor.yml"
    processor_config.write_text("type: noop\n")

    result = cli_runner.invoke(
        cli,
        [
            "postprocess",
            str(staging_dir),
            "--processor-config",
            str(processor_config),
        ],
    )

    assert result.exit_code == 0, (
        f"Expected exit 0 (skip), got: {result.exit_code}\nOutput: {result.output}\nException: {result.exception if hasattr(result, 'exception') else 'None'}"
    )

    new_content = original_sidecar.read_text()
    new_data = json.loads(new_content)
    assert new_data["updated_at"] == original_data["updated_at"], (
        "Sidecar was modified (expected idempotency skip)"
    )


def test_postprocess_reruns_when_force_specified(
    cli_runner, staging_with_successful_postprocess_result, tmp_path
):
    staging_dir, model = staging_with_successful_postprocess_result

    original_sidecar = staging_dir / POSTPROCESS_RESULT_FILENAME
    original_mtime = original_sidecar.stat().st_mtime

    import time

    time.sleep(0.01)

    processor_config = tmp_path / "processor.yml"
    processor_config.write_text("type: noop\n")

    result = cli_runner.invoke(
        cli,
        [
            "postprocess",
            str(staging_dir),
            "--processor-config",
            str(processor_config),
            "--force",
        ],
    )

    assert result.exit_code == 0, (
        f"Unexpected failure: {result.output}\nException: {result.exception if hasattr(result, 'exception') else 'None'}"
    )

    sidecar_path = staging_dir / POSTPROCESS_RESULT_FILENAME
    assert sidecar_path.exists()
    raw = json.loads(sidecar_path.read_text())
    assert raw["success"] is True

    new_mtime = sidecar_path.stat().st_mtime
    assert new_mtime > original_mtime, (
        "Sidecar file was not modified (expected reprocessing)"
    )


def test_postprocess_executes_normally_on_first_run(
    cli_runner, staging_with_run_result_only, tmp_path
):
    staging_dir, model = staging_with_run_result_only

    processor_config = tmp_path / "processor.yml"
    processor_config.write_text("type: noop\n")

    result = cli_runner.invoke(
        cli,
        [
            "postprocess",
            str(staging_dir),
            "--processor-config",
            str(processor_config),
        ],
    )

    assert result.exit_code == 0, (
        f"Unexpected failure: {result.output}\nException: {result.exception if hasattr(result, 'exception') else 'None'}"
    )

    sidecar_path = staging_dir / POSTPROCESS_RESULT_FILENAME
    assert sidecar_path.exists()
    raw = json.loads(sidecar_path.read_text())
    assert raw["kind"] == "postprocess_result"
    assert raw["success"] is True


def test_postprocess_continues_on_corrupt_postprocess_result(
    cli_runner, staging_with_run_result_only, tmp_path
):
    staging_dir, model = staging_with_run_result_only

    corrupt_sidecar = staging_dir / POSTPROCESS_RESULT_FILENAME
    corrupt_sidecar.write_text("{invalid json!!")

    processor_config = tmp_path / "processor.yml"
    processor_config.write_text("type: noop\n")

    result = cli_runner.invoke(
        cli,
        [
            "postprocess",
            str(staging_dir),
            "--processor-config",
            str(processor_config),
        ],
    )

    assert result.exit_code == 0, (
        f"Expected success despite corrupt sidecar: {result.output}\nException: {result.exception if hasattr(result, 'exception') else 'None'}"
    )

    assert corrupt_sidecar.exists()
    raw = json.loads(corrupt_sidecar.read_text())
    assert raw["kind"] == "postprocess_result"
    assert raw["success"] is True


def test_postprocess_continues_on_schema_mismatch_postprocess_result(
    cli_runner, staging_with_run_result_only, tmp_path
):
    staging_dir, model = staging_with_run_result_only

    mismatched_sidecar = staging_dir / POSTPROCESS_RESULT_FILENAME
    mismatched_sidecar.write_text(
        json.dumps(
            {
                "kind": "run_result",
                "schema_version": 1,
                "success": True,
            }
        )
    )

    processor_config = tmp_path / "processor.yml"
    processor_config.write_text("type: noop\n")

    result = cli_runner.invoke(
        cli,
        [
            "postprocess",
            str(staging_dir),
            "--processor-config",
            str(processor_config),
        ],
    )

    assert result.exit_code == 0, (
        f"Expected success despite schema mismatch: {result.output}\nException: {result.exception if hasattr(result, 'exception') else 'None'}"
    )

    new_data = json.loads(mismatched_sidecar.read_text())
    assert new_data["kind"] == "postprocess_result", (
        "Sidecar was not overwritten with correct schema"
    )
    assert new_data["success"] is True


def test_postprocess_reruns_when_previous_attempt_failed(
    cli_runner, staging_with_failed_postprocess_result, tmp_path
):
    staging_dir, model = staging_with_failed_postprocess_result

    original_sidecar = staging_dir / POSTPROCESS_RESULT_FILENAME
    original_data = json.loads(original_sidecar.read_text())
    assert original_data["success"] is False, "Fixture should create failed sidecar"

    processor_config = tmp_path / "processor.yml"
    processor_config.write_text("type: noop\n")

    result = cli_runner.invoke(
        cli,
        [
            "postprocess",
            str(staging_dir),
            "--processor-config",
            str(processor_config),
        ],
    )

    assert result.exit_code == 0, (
        f"Expected success (retry failed postprocess): {result.output}\nException: {result.exception if hasattr(result, 'exception') else 'None'}"
    )

    sidecar_path = staging_dir / POSTPROCESS_RESULT_FILENAME
    assert sidecar_path.exists()
    raw = json.loads(sidecar_path.read_text())
    assert raw["success"] is True, "Retry should succeed and update sidecar"
