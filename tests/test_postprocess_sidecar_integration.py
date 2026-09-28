"""Integration test: ModelRun.postprocess() writes postprocess_result.json sidecar."""

import json


from rompy.core.responses import ModelRunSuccess, TimingInfo
from datetime import datetime, timezone

from rompy.core.result_persistence import (
    POSTPROCESS_RESULT_FILENAME,
    load_postprocess_result,
)
from rompy.model import ModelRun
from rompy.postprocess.config import NoopPostprocessorConfig


def test_postprocess_writes_sidecar_on_success(tmp_path):
    """Verify postprocess() writes postprocess_result.json sidecar on success."""
    model = ModelRun(
        run_id="test-postprocess-success",
        output_dir=tmp_path / "output",
        run_id_subdir=True,
    )

    # Ensure staging_dir exists (NoopPostprocessor validates this)
    model.staging_dir.mkdir(parents=True, exist_ok=True)

    processor = NoopPostprocessorConfig()
    run_result = ModelRunSuccess(
        run_id=model.run_id,
        backend_used="local",
        output_dir=str(model.staging_dir),
        timing=TimingInfo(start_time=datetime.now(timezone.utc), end_time=datetime.now(timezone.utc)),
        artifacts=[], expected_outputs=[], missing_outputs=[],
    )
    result = model.postprocess(processor, processor_input=run_result)

    assert result.success is True

    sidecar_path = model.staging_dir / POSTPROCESS_RESULT_FILENAME
    assert sidecar_path.exists(), f"Sidecar file not found: {sidecar_path}"

    raw = json.loads(sidecar_path.read_text())
    assert raw["kind"] == "postprocess_result"
    assert raw["schema_version"] == 2
    assert raw["run_id"] == "test-postprocess-success"
    assert raw["success"] is True
    assert raw["status"] == "success"
    assert raw["error"] is None

    sidecar = load_postprocess_result(model.staging_dir)
    assert sidecar.success is True
    assert sidecar.run_id == "test-postprocess-success"
    assert sidecar.payload.success is True
