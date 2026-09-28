"""Frozen issue #6 corpus, adversarial validators, and fresh-process replay."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

import pytest
from pydantic import TypeAdapter, ValidationError

from rompy.core import result_persistence
from rompy.core.responses import (
    ArtifactIdentity,
    GenerateResultSidecar,
    NormalizedContext,
    PipelineResult,
    PostprocessResult,
    PostprocessResultSidecar,
    PostprocessSuccess,
    RunResultSidecar,
    ModelRunResult,
    TimingInfo,
)

FIXTURE_DIR = Path(__file__).parents[1] / "fixtures" / "return_schema_v2"
MANIFEST = FIXTURE_DIR / "manifest.json"
HANDOFF = Path("openspec/changes/implement-return-schemas/issue-6-handoff.md")
SIDECARE_TYPES = {
    "generate_result": (GenerateResultSidecar, result_persistence.load_generate_result),
    "run_result": (RunResultSidecar, result_persistence.load_run_result),
    "postprocess_result": (PostprocessResultSidecar, result_persistence.load_postprocess_result),
}


def _raw(name: str) -> dict:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


def _assert_envelope(raw: dict) -> None:
    assert raw["schema_version"] == 2
    assert raw["run_id"] == raw["payload"]["run_id"]
    assert raw["success"] == raw["payload"]["success"]
    assert raw["status"] == ("success" if raw["success"] else "failed")
    assert raw["error"] == (None if raw["success"] else raw["payload"]["error"])


def _normative_design_examples() -> list[dict]:
    source = Path("openspec/changes/implement-return-schemas/design.md")
    blocks = [
        json.loads(match.group(1))
        for match in re.finditer(r"```json\n(.*?)\n```", source.read_text(encoding="utf-8"), re.DOTALL)
    ]
    assert len(blocks) == 3, "approved design must retain exactly three bounded JSON examples"
    return blocks


def test_documented_json_examples_are_valid():
    for path in (Path("openspec/changes/implement-return-schemas/design.md"), Path("SCHEMA_DESIGN.md")):
        text = path.read_text(encoding="utf-8")
        for match in re.finditer(r"```json\n(.*?)\n```", text, re.DOTALL):
            json.loads(match.group(1))


def test_normative_examples_contract_validate_and_round_trip(tmp_path):
    success, failure, malformed = _normative_design_examples()
    success_model = RunResultSidecar.model_validate(success)
    assert RunResultSidecar.model_validate(success_model.model_dump(mode="json")).model_dump(mode="json") == success_model.model_dump(mode="json")
    failure_model = PostprocessResultSidecar.model_validate(failure)
    assert PostprocessResultSidecar.model_validate(failure_model.model_dump(mode="json")).model_dump(mode="json") == failure_model.model_dump(mode="json")
    malformed_path = tmp_path / "normative-malformed.json"
    malformed_path.write_text(json.dumps(malformed), encoding="utf-8")
    with pytest.raises(ValueError) as error:
        result_persistence.load_run_result(malformed_path)
    message = str(error.value)
    assert "envelope/payload run_id mismatch" in message
    assert "envelope/payload success mismatch" in message
    success_mismatch = deepcopy(malformed)
    success_mismatch["payload"]["run_id"] = success_mismatch["run_id"]
    with pytest.raises(ValidationError, match="envelope/payload success mismatch"):
        RunResultSidecar.model_validate(success_mismatch)


def test_handoff_hashes_match_manifest_and_fixture_bytes():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    expected = {entry["path"]: entry["sha256"] for entry in manifest["fixtures"]}
    published = {
        match.group("path"): match.group("sha")
        for match in re.finditer(
            r"^\| `(?P<path>[^`]+)` \| [^|]+ \| `(?P<sha>[0-9a-f]{64})` \|$",
            HANDOFF.read_text(encoding="utf-8"),
            re.MULTILINE,
        )
    }
    assert published == expected
    for path, digest in published.items():
        assert hashlib.sha256((FIXTURE_DIR / path).read_bytes()).hexdigest() == digest


def test_manifest_hashes_and_metadata_are_frozen():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert manifest["schema_version"] == 2
    assert {entry["kind"] for entry in manifest["fixtures"] if entry.get("expected") != "reject"} == {
        "generate_result",
        "run_result",
        "postprocess_result",
        "pipeline_result",
    }
    for entry in manifest["fixtures"]:
        path = FIXTURE_DIR / entry["path"]
        assert path.is_file()
        assert hashlib.sha256(path.read_bytes()).hexdigest() == entry["sha256"]
        if entry.get("expected") == "reject":
            assert entry["reason"] in {"malformed_json", "schema_version", "kind"}
            if entry["reason"] == "malformed_json":
                assert entry["schema_version"] is None
                assert entry["kind"] == "malformed"
                continue
            raw = json.loads(path.read_text(encoding="utf-8"))
            assert raw["schema_version"] == entry["schema_version"]
            assert raw["kind"] == entry["kind"]
            if entry["reason"] == "schema_version":
                assert raw["schema_version"] != 2
            else:
                assert raw["schema_version"] == 2
            continue
        raw = json.loads(path.read_text(encoding="utf-8"))
        for key in ("kind", "schema_version", "status", "success"):
            assert raw[key] == entry[key], f"{path}: {key} metadata mismatch"
        _assert_envelope(raw)


@pytest.mark.parametrize("name", [
    "generate_success.json", "generate_failure.json", "run_success.json",
    "run_failure.json", "postprocess_success.json", "postprocess_failure.json",
])
def test_operation_fixtures_round_trip_through_public_loader(name):
    raw = _raw(name)
    _assert_envelope(raw)
    model_type, loader = SIDECARE_TYPES[raw["kind"]]
    loaded = loader(FIXTURE_DIR / name)
    assert isinstance(loaded, model_type)
    canonical_source = model_type.model_validate(raw).model_dump(mode="json")
    canonical_loaded = loaded.model_dump(mode="json")
    assert canonical_loaded == canonical_source
    assert canonical_loaded["payload"]["run_id"] == raw["payload"]["run_id"]


@pytest.mark.parametrize("name", ["pipeline_success.json", "pipeline_failure.json"])
def test_pipeline_fixtures_round_trip_through_pipeline_adapter(name):
    raw = _raw(name)
    _assert_envelope(raw)
    payload = TypeAdapter(PipelineResult).validate_python(raw["payload"])
    canonical_source = TypeAdapter(PipelineResult).validate_python(raw["payload"]).model_dump(mode="json")
    canonical_loaded = TypeAdapter(PipelineResult).validate_python(payload.model_dump(mode="json")).model_dump(mode="json")
    assert canonical_loaded == canonical_source
    assert payload.run_id == raw["run_id"]


@pytest.mark.parametrize("name", ["run_success.json", "run_failure.json"])
def test_fresh_process_replays_typed_run_and_recording_postprocessor(name, tmp_path):
    fixture = FIXTURE_DIR / name
    script = r'''
import json
import sys
from pathlib import Path
from typing import Literal
from rompy.core.result_persistence import load_run_result
from rompy.core.responses import PostprocessSuccess
from rompy.model import ModelRun
from rompy.postprocess.config import BasePostprocessorConfig

class RecordingProcessor:
    def __init__(self, config):
        self.config = config
    def process(self, result, **options):
        assert result.__class__.__name__ in {"ModelRunSuccess", "ModelRunFailure"}
        return PostprocessSuccess(
            run_id=result.run_id,
            output_dir=result.output_dir or "fixtures/output",
            validated=True,
            timing=result.timing,
            artifacts=result.artifacts,
            expected_outputs=result.expected_outputs,
            missing_outputs=result.missing_outputs,
            metadata=result.metadata,
        )

class RecordingConfig(BasePostprocessorConfig):
    type: Literal["recording"] = "recording"
    def get_postprocessor_class(self):
        return RecordingProcessor

sidecar = load_run_result(Path(sys.argv[1]))
model = ModelRun(run_id=sidecar.payload.run_id, output_dir=Path(sys.argv[2]))
result = model.postprocess(RecordingConfig(), processor_input=sidecar.payload)
print(json.dumps({
    "received": sidecar.payload.model_dump(mode="json"),
    "returned": result.model_dump(mode="json"),
}))
'''
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(__file__).parents[2] / "src")
    completed = subprocess.run(
        [sys.executable, "-c", script, str(fixture), str(tmp_path)],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )
    observed = json.loads(completed.stdout)
    source = _raw(name)
    expected_received = TypeAdapter(ModelRunResult).validate_python(source["payload"]).model_dump(mode="json")
    received = observed["received"]
    assert received == expected_received
    expected_returned = PostprocessSuccess(
        run_id=received["run_id"],
        output_dir=received.get("output_dir") or "fixtures/output",
        validated=True,
        timing=received["timing"],
        artifacts=received["artifacts"],
        expected_outputs=received["expected_outputs"],
        missing_outputs=received["missing_outputs"],
        metadata=received["metadata"],
    ).model_dump(mode="json")
    assert TypeAdapter(PostprocessResult).validate_python(observed["returned"]).model_dump(mode="json") == expected_returned


def test_malformed_json_and_legacy_or_wrong_envelopes_rejected(tmp_path):
    wrong_kind = _raw("adversarial/wrong_kind.json")
    corrected_kind = deepcopy(wrong_kind)
    corrected_kind["kind"] = "run_result"
    for key, value in wrong_kind.items():
        if key != "kind":
            assert corrected_kind[key] == value
    corrected = RunResultSidecar.model_validate(corrected_kind)
    assert corrected.kind == "run_result"

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    for entry in manifest["fixtures"]:
        if entry.get("expected") != "reject":
            continue
        path = FIXTURE_DIR / entry["path"]
        expected = "Invalid JSON" if entry["reason"] == "malformed_json" else entry["reason"]
        with pytest.raises(ValueError, match=expected):
            result_persistence.load_run_result(path)
    source = _raw("run_success.json")
    for key, value, message in (
        ("schema_version", 1, "schema_version"),
        ("schema_version", True, "schema_version"),
        ("kind", "postprocess_result", "kind"),
        ("kind", "legacy_run", "kind"),
    ):
        candidate = deepcopy(source)
        candidate[key] = value
        path = tmp_path / f"{key}-{value}.json"
        path.write_text(json.dumps(candidate), encoding="utf-8")
        with pytest.raises(ValueError, match=message):
            result_persistence.load_run_result(path)


def test_envelope_payload_contradictions_rejected(tmp_path):
    source = _raw("run_success.json")
    for field, value, expected in (
        ("run_id", "other-run", "run_id"),
        ("success", False, "success"),
        ("status", "failed", "status"),
        ("error", "unexpected", "error"),
    ):
        candidate = deepcopy(source)
        candidate[field] = value
        path = tmp_path / f"contradiction-{field}.json"
        path.write_text(json.dumps(candidate), encoding="utf-8")
        with pytest.raises(ValueError, match=expected):
            result_persistence.load_run_result(path)
    candidate = deepcopy(source)
    del candidate["payload"]["backend_used"]
    path = tmp_path / "missing-required.json"
    path.write_text(json.dumps(candidate), encoding="utf-8")
    with pytest.raises(ValueError, match="backend_used"):
        result_persistence.load_run_result(path)


def test_timing_context_artifact_and_metadata_adversaries():
    with pytest.raises(ValidationError, match="UTC"):
        TimingInfo(start_time="2026-01-01T00:00:00", end_time="2026-01-01T00:00:01Z")
    with pytest.raises(ValidationError, match="end_time"):
        TimingInfo(start_time="2026-01-01T00:00:02Z", end_time="2026-01-01T00:00:01Z")
    with pytest.raises(ValidationError, match="duration_seconds"):
        TimingInfo(start_time="2026-01-01T00:00:00Z", end_time="2026-01-01T00:00:01Z", duration_seconds=2)
    with pytest.raises(ValidationError, match="finite"):
        TimingInfo(start_time="2026-01-01T00:00:00Z", end_time="2026-01-01T00:00:01Z", duration_seconds=float("nan"))
    with pytest.raises(ValidationError, match="finite"):
        NormalizedContext(model_type="x", period_start="2026-01-01T00:00:00Z", period_end="2026-01-01T00:00:01Z", period_interval=float("inf"), output_dir="o", staging_dir="s", config_hash="h")
    artifact = TypeAdapter(ArtifactIdentity)
    for value in ("../escape.nc", "/absolute.nc", "s3://bucket/a", "a/../b.nc"):
        with pytest.raises(ValidationError):
            artifact.validate_python({"kind": "local", "path": value})
    for value in ("file:///tmp/a", "not a uri", "s3://bucket/a b"):
        with pytest.raises(ValidationError):
            artifact.validate_python({"kind": "remote", "uri": value})


def test_pipeline_prefix_and_nested_evidence_adversaries():
    source = _raw("pipeline_failure.json")["payload"]
    for stages in ([], ["run"], ["generate", "postprocess"]):
        candidate = deepcopy(source)
        candidate["stages_completed"] = stages
        with pytest.raises(ValidationError):
            TypeAdapter(PipelineResult).validate_python(candidate)
    candidate = deepcopy(source)
    candidate["run_result"]["run_id"] = "other-run"
    with pytest.raises(ValidationError, match="run_id"):
        TypeAdapter(PipelineResult).validate_python(candidate)
    candidate = deepcopy(source)
    candidate["run_result"]["success"] = True
    with pytest.raises(ValidationError):
        TypeAdapter(PipelineResult).validate_python(candidate)
    candidate = deepcopy(source)
    candidate["run_result"]["artifacts"][0]["path"] = "../escape.nc"
    with pytest.raises(ValidationError, match="traversal"):
        TypeAdapter(PipelineResult).validate_python(candidate)
