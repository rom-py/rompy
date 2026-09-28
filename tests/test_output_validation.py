from datetime import datetime, timezone
from pathlib import Path

import pytest

from rompy.core.config import BaseConfig
from rompy.core.responses import (
    Artifact,
    ArtifactType,
    PostprocessFailure,
    PostprocessSuccess,
    ModelRunSuccess,
    TimingInfo,
)
from rompy.core.time import TimeRange
from rompy.model import ModelRun
from rompy.postprocess import NoopPostprocessor
from rompy.postprocess.config import NoopPostprocessorConfig
from tests.test_helpers import DemoConfig


def test_base_expected_artifacts_warns_and_returns_empty_list():
    config = BaseConfig()

    with pytest.warns(UserWarning, match="expected_artifacts"):
        artifacts = config.expected_artifacts()

    assert artifacts == []


def test_base_validate_outputs_warns_and_discovers_artifacts(tmp_path):
    (tmp_path / "a.yaml").write_text("x")
    (tmp_path / "b.nc").write_text("x")
    (tmp_path / "c.png").write_text("x")
    (tmp_path / "d.txt").write_text("x")
    (tmp_path / "e.bin").write_text("x")

    config = BaseConfig()
    with pytest.warns(UserWarning) as warning_records:
        artifacts = config.validate_outputs(tmp_path)

    assert any("validate_outputs" in str(w.message) for w in warning_records)
    assert any("expected_artifacts" in str(w.message) for w in warning_records)

    by_name = {Path(a.path).name: a for a in artifacts}
    assert by_name["a.yaml"].artifact_type == ArtifactType.YAML
    assert by_name["b.nc"].artifact_type == ArtifactType.NETCDF
    assert by_name["c.png"].artifact_type == ArtifactType.PLOT
    assert by_name["d.txt"].artifact_type == ArtifactType.TEXT
    assert by_name["e.bin"].artifact_type == ArtifactType.OTHER
    assert all(a.size_bytes is not None for a in artifacts)


def test_validate_outputs_warns_for_missing_expected_artifact(tmp_path):
    class ExpectedConfig(BaseConfig):
        def expected_artifacts(self):
            return [
                Artifact(
                    path="expected_restart.nc",
                    artifact_type=ArtifactType.RESTART,
                )
            ]

    config = ExpectedConfig()

    with pytest.warns(UserWarning) as warning_records:
        _ = config.validate_outputs(tmp_path)

    assert any(
        "Expected artifact not found: expected_restart.nc" in str(w.message)
        for w in warning_records
    )


def test_noop_postprocessor_discovers_files_without_config(tmp_path):
    model_run = ModelRun(
        run_id="test_run",
        period=TimeRange(
            start=datetime(2020, 2, 21, 4),
            end=datetime(2020, 2, 24, 4),
            interval="15M",
        ),
        output_dir=str(tmp_path),
        config=DemoConfig(arg1="foo", arg2="bar"),
    )

    check_dir = tmp_path / model_run.run_id
    check_dir.mkdir(parents=True, exist_ok=True)
    (check_dir / "output1.txt").write_text("test content 1")
    (check_dir / "output2.nc").write_text("test content 2")

    processor = NoopPostprocessor(NoopPostprocessorConfig())
    now = datetime.now(timezone.utc)
    run_result = ModelRunSuccess(run_id=model_run.run_id, backend_used="local", output_dir=str(check_dir), timing=TimingInfo(start_time=now, end_time=now), artifacts=[], expected_outputs=[], missing_outputs=[])
    result = processor.process(run_result, validate_outputs=True)

    assert isinstance(result, PostprocessSuccess)
    assert result.success is True
    assert len(result.artifacts) == 2
    assert result.file_count == 2
    assert all(isinstance(artifact, Artifact) for artifact in result.artifacts)
    artifact_names = {Path(a.path).name for a in result.artifacts}
    assert artifact_names == {"output1.txt", "output2.nc"}
    assert all(a.size_bytes is not None for a in result.artifacts)


def test_noop_postprocessor_rejects_duck_typed_model_run(tmp_path):
    class MinimalModelRun:
        run_id = "test-run"
        output_dir = str(tmp_path)

    minimal_model = MinimalModelRun()

    check_dir = tmp_path / minimal_model.run_id
    check_dir.mkdir(parents=True, exist_ok=True)
    (check_dir / "output1.txt").write_text("test content 1")
    (check_dir / "output2.nc").write_text("test content 2")

    processor = NoopPostprocessor(NoopPostprocessorConfig())
    result = processor.process(minimal_model, validate_outputs=True)

    assert isinstance(result, PostprocessFailure)
    assert "ModelRunResult" in result.error


def test_noop_postprocessor_with_missing_output_directory(tmp_path):
    class MinimalModelRun:
        run_id = "nonexistent-run"
        output_dir = str(tmp_path)

    minimal_model = MinimalModelRun()

    processor = NoopPostprocessor(NoopPostprocessorConfig())
    result = processor.process(minimal_model, validate_outputs=True)

    assert isinstance(result, PostprocessFailure)
    assert result.success is False
    assert "ModelRunResult" in result.error
