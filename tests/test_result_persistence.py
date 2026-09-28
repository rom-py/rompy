"""Canonical issue #4 sidecar persistence tests."""

import json
import os
from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from rompy.core import result_persistence
from rompy.core.responses import (
    GenerateResultSidecar,
    GenerateSuccess,
    LocalArtifact,
    ModelRunFailure,
    ModelRunSuccess,
    NormalizedContext,
    PostprocessResultSidecar,
    PostprocessSuccess,
    RunResultSidecar,
    TimingInfo,
)

START = datetime(2026, 3, 10, 10, 0, tzinfo=timezone.utc)


def timing(seconds: float = 1.0) -> TimingInfo:
    return TimingInfo(start_time=START, end_time=START + timedelta(seconds=seconds))


def generate_sidecar() -> GenerateResultSidecar:
    return GenerateResultSidecar(
        run_id="run-generate",
        status="success",
        success=True,
        staging_dir="staging/run-generate",
        payload=GenerateSuccess(
            run_id="run-generate",
            staging_dir="staging/run-generate",
            generated_files=["config.nml"],
            timing=timing(),
        ),
    )


def run_sidecar() -> RunResultSidecar:
    payload = ModelRunSuccess(
        run_id="run-1",
        backend_used="local",
        output_dir="results/run-1",
        timing=timing(2.25),
        artifacts=[LocalArtifact(path="outputs/waves.nc")],
        expected_outputs=[LocalArtifact(path="outputs/waves.nc")],
        missing_outputs=[LocalArtifact(path="outputs/wind.nc", reason="not produced")],
        metadata={"attempt": 1, "labels": ["canonical"]},
    )
    return RunResultSidecar(
        run_id="run-1", status="success", success=True, payload=payload
    )


def postprocess_sidecar() -> PostprocessResultSidecar:
    payload = PostprocessSuccess(
        run_id="run-1",
        output_dir="results/run-1",
        validated=True,
        timing=timing(),
        artifacts=[LocalArtifact(path="outputs/waves.nc")],
        expected_outputs=[],
        missing_outputs=[],
    )
    return PostprocessResultSidecar(
        run_id="run-1", status="success", success=True, payload=payload
    )


@pytest.mark.parametrize(
    ("writer", "loader", "sidecar", "filename"),
    [
        (
            result_persistence.write_generate_result,
            result_persistence.load_generate_result,
            generate_sidecar,
            result_persistence.GENERATE_RESULT_FILENAME,
        ),
        (
            result_persistence.write_run_result,
            result_persistence.load_run_result,
            run_sidecar,
            result_persistence.RUN_RESULT_FILENAME,
        ),
        (
            result_persistence.write_postprocess_result,
            result_persistence.load_postprocess_result,
            postprocess_sidecar,
            result_persistence.POSTPROCESS_RESULT_FILENAME,
        ),
    ],
)
def test_each_canonical_sidecar_round_trips(tmp_path, writer, loader, sidecar, filename):
    value = sidecar()
    path = writer(tmp_path, value)
    assert path == tmp_path / filename
    assert loader(path).model_dump(mode="json") == value.model_dump(mode="json")


def test_wire_json_has_numeric_duration_and_metadata(tmp_path):
    path = result_persistence.write_run_result(tmp_path, run_sidecar())
    raw = json.loads(path.read_text())
    assert raw["schema_version"] == 2
    assert raw["payload"]["timing"]["duration_seconds"] == 2.25
    assert raw["payload"]["metadata"] == {"attempt": 1, "labels": ["canonical"]}
    assert "generated_at" not in raw["payload"]


def test_nonfinite_constructed_wire_value_is_rejected_by_json_serializer(tmp_path):
    timing_value = TimingInfo.model_construct(
        start_time=START, end_time=START, duration_seconds=float("nan")
    )
    payload = ModelRunSuccess.model_construct(
        run_id="run-1",
        backend_used="local",
        output_dir="results/run-1",
        timing=timing_value,
        artifacts=[],
        expected_outputs=[],
        missing_outputs=[],
        metadata={},
        persistence_diagnostic=None,
        success=True,
        workspace_dir=None,
        message=None,
    )
    sidecar = RunResultSidecar.model_construct(
        schema_version=2,
        run_id="run-1",
        status="success",
        success=True,
        error=None,
        created_at=None,
        updated_at=None,
        staging_dir=None,
        normalized_context=None,
        kind="run_result",
        payload=payload,
    )
    with pytest.raises(ValueError, match="Out of range float values"):
        result_persistence.write_run_result(tmp_path, sidecar)


def test_repeated_writes_are_byte_deterministic(tmp_path):
    sidecar = run_sidecar()
    path = result_persistence.write_run_result(tmp_path, sidecar)
    first = path.read_bytes()
    result_persistence.write_run_result(tmp_path, sidecar)
    assert path.read_bytes() == first
    assert result_persistence.load_run_result(path).model_dump(mode="json") == sidecar.model_dump(mode="json")


def test_loaders_reject_malformed_missing_kind_version_and_legacy(tmp_path):
    path = tmp_path / result_persistence.RUN_RESULT_FILENAME
    path.write_text("not-json")
    with pytest.raises(ValueError, match="Invalid JSON"):
        result_persistence.load_run_result(path)

    path.write_text(json.dumps({"kind": "run_result", "schema_version": 2}))
    with pytest.raises(ValueError, match="Invalid canonical"):
        result_persistence.load_run_result(path)

    for version in (None, True, 1, 3):
        raw = run_sidecar().model_dump(mode="json")
        raw["schema_version"] = version
        path.write_text(json.dumps(raw))
        with pytest.raises(ValueError, match="schema_version"):
            result_persistence.load_run_result(path)

    raw = run_sidecar().model_dump(mode="json")
    raw["kind"] = "legacy_result"
    path.write_text(json.dumps(raw))
    with pytest.raises(ValueError, match="kind"):
        result_persistence.load_run_result(path)


def test_loader_rejects_envelope_payload_mismatches(tmp_path):
    path = result_persistence.write_run_result(tmp_path, run_sidecar())
    raw = json.loads(path.read_text())
    raw["payload"]["run_id"] = "different"
    path.write_text(json.dumps(raw))
    with pytest.raises(ValueError, match="run_id"):
        result_persistence.load_run_result(path)

    raw = run_sidecar().model_dump(mode="json")
    raw["status"] = "failed"
    path.write_text(json.dumps(raw))
    with pytest.raises(ValueError, match="status"):
        result_persistence.load_run_result(path)


def test_write_failure_cleans_temp_and_preserves_existing_destination(tmp_path, monkeypatch):
    path = result_persistence.write_run_result(tmp_path, run_sidecar())
    previous = path.read_bytes()
    real_fdopen = result_persistence.os.fdopen

    class FailingStream:
        def __init__(self, fd):
            self.fd = fd

        def __enter__(self):
            return self

        def __exit__(self, *_):
            os.close(self.fd)

        def write(self, _data):
            raise OSError("interrupted temp write")

        def flush(self):
            return None

        def fileno(self):
            return self.fd

    monkeypatch.setattr(result_persistence.os, "fdopen", lambda fd, mode: FailingStream(fd))
    with pytest.raises(OSError, match="interrupted temp write"):
        result_persistence.write_run_result(tmp_path, run_sidecar())
    assert path.read_bytes() == previous
    assert list(tmp_path.glob(".run_result.json.*")) == []
    monkeypatch.setattr(result_persistence.os, "fdopen", real_fdopen)


def test_persist_result_returns_typed_failure_without_primary_error(tmp_path, monkeypatch):
    result = run_sidecar().payload
    monkeypatch.setattr(
        result_persistence,
        "_atomic_write",
        lambda *_: (_ for _ in ()).throw(OSError("temp write failed")),
    )
    returned = result_persistence.persist_result(result, run_sidecar(), tmp_path)
    assert isinstance(returned, ModelRunFailure)
    assert returned.error == "temp write failed"
    assert returned.persistence_diagnostic.error == "temp write failed"
    assert returned.persistence_diagnostic.primary_error is None


def test_persist_result_preserves_supplied_primary_error(tmp_path, monkeypatch):
    failure = ModelRunFailure(
        run_id="run-1",
        backend_used="local",
        error="model operation failed",
        timing=timing(),
        artifacts=[],
        expected_outputs=[],
        missing_outputs=[],
    )
    sidecar = RunResultSidecar(
        run_id="run-1",
        status="failed",
        success=False,
        error="model operation failed",
        payload=failure,
    )
    monkeypatch.setattr(
        result_persistence,
        "_atomic_write",
        lambda *_: (_ for _ in ()).throw(OSError("directory fsync failed")),
    )
    returned = result_persistence.persist_result(
        failure, sidecar, tmp_path, primary_error="model operation failed"
    )
    assert isinstance(returned, ModelRunFailure)
    assert returned.error == "model operation failed"
    assert returned.persistence_diagnostic.error == "directory fsync failed"
    assert returned.persistence_diagnostic.primary_error == "model operation failed"


def test_persist_result_handles_mutated_metadata_without_rethrow(tmp_path):
    sidecar = run_sidecar()
    result = sidecar.payload
    result.metadata["mutated"] = object()

    returned = result_persistence.persist_result(
        result, sidecar, tmp_path, primary_error="operation failed"
    )
    assert isinstance(returned, ModelRunFailure)
    assert returned.error == "operation failed"
    assert returned.persistence_diagnostic.primary_error == "operation failed"
    diagnostic_error = returned.persistence_diagnostic.error.lower()
    assert "serializ" in diagnostic_error or "not json" in diagnostic_error
    assert returned.metadata == {}
    assert not (tmp_path / result_persistence.RUN_RESULT_FILENAME).exists()
    assert list(tmp_path.glob(".run_result.json.*")) == []


def test_replace_failure_cleans_temp_and_preserves_existing_destination(tmp_path, monkeypatch):
    path = result_persistence.write_run_result(tmp_path, run_sidecar())
    previous = path.read_bytes()
    monkeypatch.setattr(
        result_persistence.os,
        "replace",
        lambda *_: (_ for _ in ()).throw(OSError("replace failed")),
    )
    with pytest.raises(OSError, match="replace failed"):
        result_persistence.write_run_result(tmp_path, run_sidecar())
    assert path.read_bytes() == previous
    assert list(tmp_path.glob(".run_result.json.*")) == []


def test_directory_fsync_failure_is_observable_and_cleans_temp(tmp_path, monkeypatch):
    path = result_persistence.write_run_result(tmp_path, run_sidecar())
    previous = path.read_bytes()
    calls = 0
    real_fsync = result_persistence.os.fsync

    def fail_directory_sync(fd):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("directory fsync failed")
        return real_fsync(fd)

    monkeypatch.setattr(result_persistence.os, "fsync", fail_directory_sync)
    with pytest.raises(OSError, match="directory fsync failed"):
        result_persistence.write_run_result(tmp_path, run_sidecar())
    assert path.exists()
    assert path.read_bytes() != b""
    assert list(tmp_path.glob(".run_result.json.*")) == []
    assert path.read_bytes() != previous or calls == 2


def test_non_serializable_metadata_is_rejected_before_filesystem_write(tmp_path):
    with pytest.raises(ValidationError, match="JSON-safe"):
        ModelRunSuccess(
            run_id="run-1",
            backend_used="local",
            output_dir="results/run-1",
            timing=timing(),
            metadata={"bad": object()},
        )
    assert list(tmp_path.iterdir()) == []


def test_nonfinite_numeric_values_are_rejected_and_not_written(tmp_path):
    for value in (float("nan"), float("inf"), float("-inf")):
        with pytest.raises(ValidationError, match="finite"):
            NormalizedContext(
                model_type="ww3",
                period_start=START,
                period_end=START + timedelta(days=1),
                period_interval=value,
                output_dir="results",
                staging_dir="staging",
                config_hash="abc",
            )
        with pytest.raises(ValidationError, match="finite"):
            TimingInfo(start_time=START, end_time=START, duration_seconds=value)
    assert list(tmp_path.iterdir()) == []


def test_normalized_context_uses_numeric_interval():
    context = NormalizedContext(
        model_type="ww3",
        period_start=START,
        period_end=START + timedelta(days=1),
        period_interval=3600,
        output_dir="results",
        staging_dir="staging",
        config_hash="abc",
    )
    assert context.period_interval == 3600.0
    with pytest.raises(ValidationError, match="numeric"):
        NormalizedContext(
            model_type="ww3",
            period_start=START,
            period_end=START + timedelta(days=1),
            period_interval="1h",
            output_dir="results",
            staging_dir="staging",
            config_hash="abc",
        )