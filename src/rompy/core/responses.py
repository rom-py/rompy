"""Canonical, validated result schemas and sidecar envelope models.

The result unions in this module are typing aliases.  Use ``TypeAdapter`` (or
one of the concrete sidecar loaders) to deserialize a union.
"""

from __future__ import annotations

import json
import math
import re
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import PurePosixPath
from typing import Annotated, Any, Literal
from urllib.parse import urlsplit

from pydantic import (
    Field,
    StrictInt,
    StringConstraints,
    field_validator,
    model_validator,
)

from rompy.core.types import RompyBaseModel

UTC = timezone.utc

# Failure details are part of the durable contract and must always be useful.
# ``strip_whitespace`` also rejects whitespace-only adversarial inputs while
# preserving ordinary error text.
NonEmptyError = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


def _utc(value: datetime, field: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() != timedelta(0):
        raise ValueError(f"{field} must be timezone-aware UTC")
    return value


def _json_safe(value: dict[str, Any]) -> dict[str, Any]:
    try:
        json.dumps(value, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ValueError("metadata must contain only JSON-safe values") from exc
    return value


def _local_path(value: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value:
        raise ValueError("local artifact path must be a non-empty POSIX path")
    if value.startswith("/") or re.match(r"^[A-Za-z]:", value):
        raise ValueError("local artifact path must be staging-relative, not absolute")
    parsed = urlsplit(value)
    if parsed.scheme or parsed.netloc or "://" in value:
        raise ValueError("URI-like values must use the remote artifact variant")
    path = PurePosixPath(value)
    parts = path.parts
    if not parts or any(part in ("", ".", "..") for part in parts):
        raise ValueError("local artifact path must not contain traversal components")
    normalized = path.as_posix()
    if normalized != value:
        raise ValueError("local artifact path must be normalized POSIX syntax")
    return value


def _remote_uri(value: str) -> str:
    if not isinstance(value, str) or not value or any(ch.isspace() for ch in value):
        raise ValueError("remote artifact URI must be a non-empty URI")
    parsed = urlsplit(value)
    if not parsed.scheme or parsed.scheme.lower() == "file":
        raise ValueError("remote artifact URI must use a non-file URI scheme")
    return value


class NormalizedContext(RompyBaseModel):
    """Plugin-neutral context persisted with generation/run sidecars."""

    model_type: str
    period_start: datetime
    period_end: datetime
    period_interval: float
    output_dir: str
    staging_dir: str
    config_hash: str
    extensions: dict[str, Any] = Field(default_factory=dict)

    _period_start_utc = field_validator("period_start")(lambda value: _utc(value, "period_start"))
    _period_end_utc = field_validator("period_end")(lambda value: _utc(value, "period_end"))

    @field_validator("period_interval", mode="before")
    @classmethod
    def numeric_interval(cls, value: Any) -> float:
        if isinstance(value, (str, bool)) or not isinstance(value, (int, float)):
            raise ValueError("period_interval must be numeric seconds")  # noqa: TRY004
        try:
            numeric = float(value)
        except OverflowError as exc:
            raise ValueError("period_interval must be finite numeric seconds") from exc
        if not math.isfinite(numeric):
            raise ValueError("period_interval must be finite numeric seconds")
        if numeric < 0:
            raise ValueError("period_interval must be nonnegative")
        return numeric

    @model_validator(mode="after")
    def ordered_period(self) -> NormalizedContext:
        if self.period_end < self.period_start:
            raise ValueError("period_end must be greater than or equal to period_start")
        return self


class PipelineStage(str, Enum):
    GENERATE = "generate"
    RUN = "run"
    POSTPROCESS = "postprocess"


class ArtifactType(str, Enum):
    YAML = "yaml"
    NETCDF = "netcdf"
    PLOT = "plot"
    TEXT = "text"
    RESTART = "restart"
    OTHER = "other"


class LocalArtifact(RompyBaseModel):
    kind: Literal["local"] = "local"
    path: str
    artifact_type: ArtifactType | None = None
    size_bytes: int | None = None
    description: str | None = None
    date: str | None = None
    reason: str | None = None

    _valid_path = field_validator("path")(_local_path)


class RemoteArtifact(RompyBaseModel):
    kind: Literal["remote"] = "remote"
    uri: str
    artifact_type: ArtifactType | None = None
    size_bytes: int | None = None
    description: str | None = None
    date: str | None = None
    reason: str | None = None

    _valid_uri = field_validator("uri")(_remote_uri)


# Artifact is retained as the local concrete spelling used by existing core
# callers.  Canonical collections use the explicit local/remote union.
Artifact = LocalArtifact
ArtifactIdentity = Annotated[
    LocalArtifact | RemoteArtifact, Field(discriminator="kind")
]
# Descriptive aliases make the two wire variants discoverable to consumers.
LocalArtifactIdentity = LocalArtifact
RemoteArtifactIdentity = RemoteArtifact
OutputEvidence = ArtifactIdentity
ExpectedOutput = ArtifactIdentity
MissingOutput = ArtifactIdentity


class TimingInfo(RompyBaseModel):
    start_time: datetime
    end_time: datetime
    duration_seconds: float | None = None

    _start_utc = field_validator("start_time")(
        lambda value: _utc(value, "start_time")
    )
    _end_utc = field_validator("end_time")(lambda value: _utc(value, "end_time"))

    @field_validator("duration_seconds", mode="before")
    @classmethod
    def numeric_duration(cls, value: Any) -> Any:
        if value is None:
            return value
        if isinstance(value, (str, bool)) or not isinstance(value, (int, float)):
            raise ValueError("duration_seconds must be numeric seconds")  # noqa: TRY004
        try:
            numeric = float(value)
        except OverflowError as exc:
            raise ValueError("duration_seconds must be finite numeric seconds") from exc
        if not math.isfinite(numeric):
            raise ValueError("duration_seconds must be finite numeric seconds")
        return numeric

    @model_validator(mode="after")
    def validate_interval(self) -> TimingInfo:
        if self.end_time < self.start_time:
            raise ValueError("end_time must be greater than or equal to start_time")
        expected = (self.end_time - self.start_time).total_seconds()
        if self.duration_seconds is not None and self.duration_seconds != expected:
            raise ValueError(
                f"duration_seconds {self.duration_seconds} does not match timestamps ({expected})"
            )
        object.__setattr__(self, "duration_seconds", expected)
        return self


class PersistenceDiagnostic(RompyBaseModel):
    status: Literal["failed"] = "failed"
    sidecar_kind: str
    sidecar_path: str
    error: NonEmptyError
    primary_error: NonEmptyError | None = None


class _ResultBase(RompyBaseModel):
    run_id: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    persistence_diagnostic: PersistenceDiagnostic | None = None

    _metadata_json = field_validator("metadata")(_json_safe)

    @model_validator(mode="after")
    def persisted_success_is_impossible(self):
        if getattr(self, "success", False) and self.persistence_diagnostic is not None:
            raise ValueError("successful result cannot carry a persistence diagnostic")
        return self


class GenerateSuccess(_ResultBase):
    success: Literal[True] = True
    staging_dir: str
    generated_files: list[str]
    timing: TimingInfo
    config_file: str | None = None


class GenerateFailure(_ResultBase):
    success: Literal[False] = False
    error: NonEmptyError
    generated_files: list[str]
    timing: TimingInfo
    staging_dir: str | None = None
    config_file: str | None = None


GenerateResult = Annotated[
    GenerateSuccess | GenerateFailure, Field(discriminator="success")
]


class _ExecutionEvidence(_ResultBase):
    artifacts: list[ArtifactIdentity]
    expected_outputs: list[ArtifactIdentity]
    missing_outputs: list[ArtifactIdentity]


class ModelRunSuccess(_ExecutionEvidence):
    success: Literal[True] = True
    backend_used: str
    output_dir: str
    timing: TimingInfo
    workspace_dir: str | None = None
    message: str | None = None


class ModelRunFailure(_ExecutionEvidence):
    success: Literal[False] = False
    backend_used: str
    error: NonEmptyError
    timing: TimingInfo
    output_dir: str | None = None
    workspace_dir: str | None = None
    message: str | None = None


ModelRunResult = Annotated[
    ModelRunSuccess | ModelRunFailure, Field(discriminator="success")
]


class PostprocessSuccess(_ExecutionEvidence):
    success: Literal[True] = True
    output_dir: str
    validated: bool
    timing: TimingInfo
    file_count: int | None = None
    message: str | None = None


class PostprocessFailure(_ExecutionEvidence):
    success: Literal[False] = False
    error: NonEmptyError
    timing: TimingInfo
    output_dir: str | None = None
    message: str | None = None


PostprocessResult = Annotated[
    PostprocessSuccess | PostprocessFailure, Field(discriminator="success")
]


class StageTiming(RompyBaseModel):
    stage: PipelineStage
    timing: TimingInfo


class PipelineSuccess(_ResultBase):
    success: Literal[True] = True
    stages_completed: list[PipelineStage]
    backend: str
    processor: str
    staging_dir: str
    output_dir: str
    postprocess_results: PostprocessSuccess
    timing: TimingInfo
    stage_timings: list[StageTiming]
    workspace_dir: str | None = None
    message: str | None = None

    @model_validator(mode="after")
    def validate_success_stages(self):
        if self.stages_completed != list(PipelineStage):
            raise ValueError("successful pipeline must complete generate, run, postprocess")
        if self.postprocess_results.run_id != self.run_id:
            raise ValueError("pipeline and postprocess run_id must match")
        return self


class PipelineFailure(_ResultBase):
    success: Literal[False] = False
    stages_completed: list[PipelineStage]
    backend: str
    processor: str
    failed_stage: PipelineStage
    error: NonEmptyError
    timing: TimingInfo
    stage_timings: list[StageTiming] = Field(default_factory=list)
    cleaned_up: bool
    staging_dir: str | None = None
    workspace_dir: str | None = None
    output_dir: str | None = None
    generate_result: GenerateFailure | None = None
    run_result: ModelRunFailure | None = None
    postprocess_results: PostprocessFailure | None = None
    message: str | None = None

    @model_validator(mode="after")
    def validate_failure_stages(self):
        stages = list(PipelineStage)
        expected = stages[: stages.index(self.failed_stage)]
        if self.stages_completed != expected:
            raise ValueError(
                f"stages_completed must be the successful prefix before {self.failed_stage.value}"
            )
        nested = {
            PipelineStage.GENERATE: self.generate_result,
            PipelineStage.RUN: self.run_result,
            PipelineStage.POSTPROCESS: self.postprocess_results,
        }
        failed_result = nested[self.failed_stage]
        if failed_result is not None and failed_result.run_id != self.run_id:
            raise ValueError("pipeline and nested stage run_id must match")
        if self.failed_stage is PipelineStage.POSTPROCESS:
            if self.postprocess_results is None:
                raise ValueError("postprocess failure must retain postprocess_results")
        elif self.postprocess_results is not None:
            raise ValueError("postprocess_results is only valid for postprocess failure")
        if self.failed_stage is not PipelineStage.GENERATE and self.generate_result is not None:
            raise ValueError("generate_result is only valid for generate failure")
        if self.failed_stage is not PipelineStage.RUN and self.run_result is not None:
            raise ValueError("run_result is only valid for run failure")
        return self


PipelineResult = Annotated[
    PipelineSuccess | PipelineFailure, Field(discriminator="success")
]


class _SidecarBase(RompyBaseModel):
    schema_version: StrictInt = 2
    run_id: str
    status: Literal["success", "failed"]
    success: bool
    error: NonEmptyError | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    staging_dir: str | None = None
    normalized_context: NormalizedContext | None = None

    @field_validator("success", mode="before")
    @classmethod
    def strict_success(cls, value: Any) -> bool:
        if not isinstance(value, bool):
            raise ValueError("success must be a boolean")  # noqa: TRY004
        return value

    @field_validator("schema_version", mode="before")
    @classmethod
    def current_version(cls, value: Any) -> int:
        if isinstance(value, bool) or not isinstance(value, int) or value != 2:
            raise ValueError(
                f"Unsupported schema_version {value!r}; regenerate a canonical schema_version 2 sidecar"
            )
        return value

    @field_validator("created_at", "updated_at")
    @classmethod
    def envelope_timestamp(cls, value: datetime | None) -> datetime | None:
        return None if value is None else _utc(value, "sidecar timestamp")

    def _coherent(self, payload: Any, expected_kind: str) -> None:
        mismatches = []
        if self.run_id != payload.run_id:
            mismatches.append(
                f"envelope/payload run_id mismatch: {self.run_id!r} != {payload.run_id!r}"
            )
        if self.success != payload.success:
            mismatches.append(
                f"envelope/payload success mismatch: {self.success!r} != {payload.success!r}"
            )
        if mismatches:
            raise ValueError("; ".join(mismatches))
        expected_status = "success" if payload.success else "failed"
        if self.status != expected_status:
            raise ValueError(
                f"status {self.status!r} disagrees with payload success; expected {expected_status!r}"
            )
        payload_error = getattr(payload, "error", None)
        if self.success and (self.error is not None or payload_error is not None):
            raise ValueError("successful envelope/payload cannot contain an error")
        if not self.success and (not self.error or self.error != payload_error):
            raise ValueError("failed envelope error must match payload error")


class GenerateResultSidecar(_SidecarBase):
    kind: Literal["generate_result"] = "generate_result"
    payload: GenerateResult

    @model_validator(mode="after")
    def coherent(self):
        self._coherent(self.payload, self.kind)
        return self


class RunResultSidecar(_SidecarBase):
    kind: Literal["run_result"] = "run_result"
    payload: ModelRunResult

    @model_validator(mode="after")
    def coherent(self):
        self._coherent(self.payload, self.kind)
        return self


class PostprocessResultSidecar(_SidecarBase):
    kind: Literal["postprocess_result"] = "postprocess_result"
    payload: PostprocessResult

    @model_validator(mode="after")
    def coherent(self):
        self._coherent(self.payload, self.kind)
        return self