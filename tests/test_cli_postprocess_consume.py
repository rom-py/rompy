"""Focused fresh-process/sidecar postprocess handoff tests."""

from datetime import datetime, timezone
from rompy.cli import _build_postprocess_processor_input
from rompy.core.responses import LocalArtifact, ModelRunSuccess, TimingInfo


def test_fresh_process_reconstruction_preserves_context_and_evidence(tmp_path):
    now = datetime.now(timezone.utc)
    result = ModelRunSuccess(
        run_id="fresh-run",
        backend_used="local",
        output_dir=str(tmp_path),
        workspace_dir=str(tmp_path),
        timing=TimingInfo(start_time=now, end_time=now),
        artifacts=[LocalArtifact(path="outputs/waves.nc")],
        expected_outputs=[LocalArtifact(path="outputs/waves.nc")],
        missing_outputs=[LocalArtifact(path="outputs/wind.nc", reason="not produced")],
        metadata={"normalized_context": {"model_type": "base", "interval": 3600}},
    )

    class Sidecar:
        payload = result
        normalized_context = {"model_type": "base", "period_interval": 3600}

    restored = _build_postprocess_processor_input(Sidecar())
    assert restored is result
    assert restored.artifacts == result.artifacts
    assert restored.expected_outputs == result.expected_outputs
    assert restored.missing_outputs == result.missing_outputs
    assert restored.metadata == result.metadata


def test_remote_and_local_artifacts_are_not_path_filtered(tmp_path):
    now = datetime.now(timezone.utc)
    result = ModelRunSuccess(
        run_id="fresh-run",
        backend_used="local",
        output_dir=str(tmp_path),
        timing=TimingInfo(start_time=now, end_time=now),
        artifacts=[
            LocalArtifact(path="missing/not-on-disk.nc"),
        ],
        expected_outputs=[],
        missing_outputs=[],
    )
    sidecar = type("Sidecar", (), {"payload": result})()
    assert _build_postprocess_processor_input(sidecar).artifacts == result.artifacts
