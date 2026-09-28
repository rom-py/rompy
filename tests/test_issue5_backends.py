"""Typed workspace generation coverage for all execution backends."""

from datetime import datetime, timezone
from unittest.mock import Mock, patch

from rompy.backends.config import DockerConfig, LocalConfig, SlurmConfig
from rompy.core.responses import GenerateFailure, GenerateSuccess, TimingInfo
from rompy.run import LocalRunBackend
from rompy.run.docker import DockerRunBackend
from rompy.run.slurm import SlurmRunBackend
from rompy.model import ModelRun
from rompy.core.result_persistence import load_run_result


def generated(path, failure=False):
    now = datetime.now(timezone.utc)
    if failure:
        return GenerateFailure(run_id="run-5", error="render failed", staging_dir=str(path), generated_files=[], timing=TimingInfo(start_time=now, end_time=now))
    return GenerateSuccess(run_id="run-5", staging_dir=str(path), generated_files=[], timing=TimingInfo(start_time=now, end_time=now))


def model(tmp_path):
    value = Mock(run_id="run-5", output_dir=tmp_path)
    value.generate.return_value = generated(tmp_path)
    return value


def test_local_backend_unwraps_typed_workspace_and_propagates_failure(tmp_path):
    value = model(tmp_path)
    (tmp_path / "run-5").mkdir()
    backend = LocalRunBackend()
    with patch.object(value, "generate", return_value=generated(tmp_path / "run-5")):
        assert backend.run(value, LocalConfig(command="true", working_dir=tmp_path / "run-5")) is True
    assert isinstance(backend.generate_result, GenerateSuccess)
    with patch.object(value, "generate", return_value=generated(tmp_path, failure=True)):
        assert backend.run(value, LocalConfig(command="true", working_dir=tmp_path)) is False
    assert backend.generate_result.error == "render failed"


def test_docker_backend_unwraps_typed_workspace_and_failure(tmp_path):
    value = model(tmp_path)
    backend = DockerRunBackend()
    config = DockerConfig(image="test-image")
    with patch.object(value, "generate", return_value=generated(tmp_path)), patch.object(backend, "_prepare_image", return_value="test-image"), patch.object(backend, "_run_container", return_value=True):
        assert backend.run(value, config) is True
    assert isinstance(backend.generate_result, GenerateSuccess)
    with patch.object(value, "generate", return_value=generated(tmp_path, failure=True)):
        assert backend.run(value, config) is False
    assert backend.generate_result.error == "render failed"


def test_model_run_uses_local_typed_generated_workspace_and_persists(tmp_path):
    model_run = ModelRun(run_id="run-5", output_dir=tmp_path)
    workspace = tmp_path / "generated"
    workspace.mkdir()
    with patch.object(ModelRun, "generate", return_value=generated(workspace)), patch("rompy.run.LocalRunBackend._execute_command", return_value=True):
        result = model_run.run(LocalConfig(command="true", working_dir=workspace))
    assert result.success is True
    assert result.workspace_dir == str(workspace)
    assert load_run_result(workspace).payload.workspace_dir == str(workspace)


def test_model_run_preserves_local_generation_failure_path(tmp_path):
    model_run = ModelRun(run_id="run-5", output_dir=tmp_path)
    workspace = tmp_path / "generated"
    workspace.mkdir()
    failure = generated(workspace, failure=True)
    with patch.object(ModelRun, "generate", return_value=failure):
        result = model_run.run(LocalConfig(command="true"))
    assert result.success is False
    assert result.workspace_dir == str(workspace)
    assert result.error == "render failed"
    assert load_run_result(workspace).payload.error == "render failed"


def test_model_run_uses_docker_typed_generated_workspace(tmp_path):
    model_run = ModelRun(run_id="run-5", output_dir=tmp_path)
    workspace = tmp_path / "docker-generated"
    workspace.mkdir()
    with patch.object(ModelRun, "generate", return_value=generated(workspace)), patch.object(DockerRunBackend, "_prepare_image", return_value="image"), patch.object(DockerRunBackend, "_run_container", return_value=True):
        result = model_run.run(DockerConfig(image="image"))
    assert result.success is True
    assert result.workspace_dir == str(workspace)
    assert load_run_result(workspace).payload.workspace_dir == str(workspace)


def test_model_run_uses_slurm_typed_generated_workspace(tmp_path):
    model_run = ModelRun(run_id="run-5", output_dir=tmp_path)
    workspace = tmp_path / "slurm-generated"
    workspace.mkdir()
    with patch.object(ModelRun, "generate", return_value=generated(workspace)), patch.object(SlurmRunBackend, "_create_job_script", return_value="job.sh"), patch.object(SlurmRunBackend, "_submit_job", return_value="42"), patch.object(SlurmRunBackend, "_wait_for_completion", return_value=True):
        result = model_run.run(SlurmConfig(command="true"))
    assert result.success is True
    assert result.workspace_dir == str(workspace)
    assert load_run_result(workspace).payload.workspace_dir == str(workspace)


def test_slurm_backend_unwraps_typed_workspace_and_failure(tmp_path):
    value = model(tmp_path)
    backend = SlurmRunBackend()
    config = SlurmConfig(command="true")
    with patch.object(value, "generate", return_value=generated(tmp_path)), patch.object(backend, "_create_job_script", return_value="job.sh"), patch.object(backend, "_submit_job", return_value="42"), patch.object(backend, "_wait_for_completion", return_value=True):
        assert backend.run(value, config) is True
    assert isinstance(backend.generate_result, GenerateSuccess)
    with patch.object(value, "generate", return_value=generated(tmp_path, failure=True)):
        assert backend.run(value, config) is False
    assert backend.generate_result.error == "render failed"
