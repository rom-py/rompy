"""Model-neutral, retry-safe transfer postprocessor."""
from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from pydantic import Field, field_validator, model_validator

from rompy.core.artifacts import compute_source_checksum, stable_artifact_identity
from rompy.core.responses import (
    ArtifactType,
    LocalArtifact,
    PostprocessFailure,
    PostprocessSuccess,
    RemoteArtifact,
    TimingInfo,
)
from rompy.transfer.registry import get_transfer
from rompy.transfer.utils import redact_error

from .config import BasePostprocessorConfig
from .protocol import (
    PostprocessContext,
    PostprocessFailurePolicy,
    validate_state_namespace,
)


def normalize_destination(destination: str) -> str:
    """Return a non-secret destination identity for evidence and state.

    Query strings and fragments are deliberately discarded.  A signed URL is
    executable input to a transfer backend, never an artifact identity.
    """
    value = str(destination).strip()
    parsed = urlsplit(value)
    if not parsed.scheme:
        return value.split("#", 1)[0].split("?", 1)[0]
    host = parsed.hostname or ""
    if parsed.port:
        host = f"{host}:{parsed.port}"
    return urlunsplit((parsed.scheme.lower(), host, parsed.path, "", ""))


def _join(destination: str, name: str) -> str:
    """Join a redacted destination identity and basename."""
    return normalize_destination(destination).rstrip("/") + "/" + name.lstrip("/")


def _join_live(destination: str, name: str) -> str:
    """Join executable destination material for the transfer backend.

    Local ``file://`` targets cannot use URI credentials and are normalized to
    avoid carrying them into a filesystem adapter.  Network/cloud targets
    retain their original signed URL material for the live call only.
    """
    parsed = urlsplit(destination)
    if parsed.scheme.lower() == "file":
        destination = normalize_destination(destination)
        parsed = urlsplit(destination)
    if parsed.scheme:
        path = parsed.path.rstrip("/") + "/" + name.lstrip("/")
        return urlunsplit((parsed.scheme, parsed.netloc, path, parsed.query, parsed.fragment))
    return str(destination).rstrip("/") + "/" + name.lstrip("/")


def _redact(value: object, destinations: tuple[str, ...], live_targets: tuple[str, ...] = ()) -> str:
    """Remove raw and percent-decoded URL credentials from diagnostics."""
    return redact_error(value, *(destinations + live_targets))


def _remote_evidence(uri: str, artifact_type: ArtifactType | None):
    if urlsplit(uri).scheme.lower() == "file":
        return None
    return RemoteArtifact(uri=normalize_destination(uri), artifact_type=artifact_type)


def _default_name(artifact: LocalArtifact) -> str:
    return Path(artifact.path).name


class TransferPostprocessorConfig(BasePostprocessorConfig):
    """Configuration for generic destination fan-out."""

    type: str = "transfer"
    destinations: list[str] = Field(min_length=1)
    artifact_types: list[ArtifactType] | None = None
    required: bool = True
    required_outputs: bool | None = None
    failure_policy: PostprocessFailurePolicy = PostprocessFailurePolicy.CONTINUE
    max_retries: int = Field(0, ge=0, le=20)
    state_namespace: str = "transfer"

    @field_validator("state_namespace")
    @classmethod
    def validate_state_namespace_field(cls, value: str) -> str:
        return validate_state_namespace(value)

    @model_validator(mode="after")
    def apply_required_alias(self):
        if self.required_outputs is not None:
            self.required = self.required_outputs
        return self

    def get_postprocessor_class(self):
        return TransferPostprocessor


class TransferPostprocessor:
    """Transfer local artifacts while persisting only redacted evidence."""

    name = "transfer"
    input_protocol = "context"

    def __init__(
        self,
        config: TransferPostprocessorConfig,
        target_naming: Callable[[LocalArtifact], str] | None = None,
    ):
        self.config = config
        self.target_naming = target_naming or _default_name
        self._state_updates: dict[str, dict[str, Any]] = {}

    def _state_paths(self, context: PostprocessContext) -> tuple[Path, Path, Path]:
        """Resolve state paths below one canonical postprocess root."""
        validate_state_namespace(self.config.state_namespace)
        base = context.staging_dir or context.output_dir
        if base is None:
            raise ValueError("no staging or output directory is available for transfer state")
        base_path = Path(base).expanduser().resolve(strict=False)
        root = (base_path / ".rompy-postprocess").resolve(strict=False)
        namespace = (root / self.config.state_namespace).resolve(strict=False)
        try:
            namespace.relative_to(root)
        except ValueError as exc:
            raise ValueError("transfer state namespace escapes .rompy-postprocess") from exc
        return root, namespace / "transfer.lock", namespace / "transfer-state.json"

    def _lock(self, context: PostprocessContext):
        root, path, state_path = self._state_paths(context)
        root.mkdir(parents=True, exist_ok=True)
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError as exc:
            raise RuntimeError("transfer state is locked") from exc
        os.close(fd)
        return path, state_path

    @staticmethod
    def _load_state(path: Path) -> dict[str, dict[str, Any]]:
        try:
            value = json.loads(path.read_text())
        except FileNotFoundError:
            return {}
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"invalid transfer replay state: {exc}") from exc
        if not isinstance(value, dict) or any(not isinstance(item, dict) for item in value.values()):
            raise ValueError("invalid transfer replay state: expected an object of records")
        return value

    @staticmethod
    def _write_state(path: Path, state: dict[str, dict[str, Any]]) -> None:
        temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
        temporary.write_text(json.dumps(state, sort_keys=True, separators=(",", ":")))
        os.replace(temporary, path)

    def _source_path(self, context: PostprocessContext, artifact: LocalArtifact) -> Path:
        root = context.output_dir or context.staging_dir
        if root is None:
            raise FileNotFoundError("no output workspace is available")
        path = (Path(root) / artifact.path).resolve(strict=False)
        workspace = Path(root).resolve(strict=False)
        try:
            path.relative_to(workspace)
        except ValueError as exc:
            raise ValueError("local artifact escapes output workspace") from exc
        return path

    def process(self, context: PostprocessContext):
        start = datetime.now(timezone.utc)
        destinations = tuple(str(item) for item in self.config.destinations)
        lock = None
        try:
            lock, state_path = self._lock(context)
            replay_state = self._load_state(state_path)
            # Disk state is the authority for a fresh process.  In-process
            # retries use this processor's redacted updates; arbitrary caller
            # operational state is never copied into persisted transfer state.
            prior = dict(replay_state)
            prior.update(self._state_updates)
            reconciliation = context.reconcile_artifacts(artifact_types=self.config.artifact_types)
            required_missing = reconciliation.missing
            if self.config.artifact_types:
                allowed = set(self.config.artifact_types)
                required_missing = [item for item in required_missing if item.artifact_type in allowed]
            if self.config.required and required_missing:
                missing = ", ".join(stable_artifact_identity(item) for item in required_missing)
                return PostprocessFailure(
                    run_id=context.run_result.run_id,
                    error=f"required source artifacts are missing: {missing}",
                    output_dir=str(context.output_dir) if context.output_dir else None,
                    artifacts=list(context.artifacts),
                    expected_outputs=list(context.expected_outputs),
                    missing_outputs=list(context.missing_outputs),
                    timing=TimingInfo(start_time=start, end_time=datetime.now(timezone.utc)),
                )
            sources = [item for item in reconciliation.selected if isinstance(item, LocalArtifact)]
            if not sources:
                return PostprocessSuccess(
                    run_id=context.run_result.run_id,
                    output_dir=str(context.output_dir or ""),
                    validated=True,
                    artifacts=list(context.artifacts),
                    expected_outputs=list(context.expected_outputs),
                    missing_outputs=list(context.missing_outputs),
                    file_count=0,
                    message="No transferable artifacts selected",
                    timing=TimingInfo(start_time=start, end_time=datetime.now(timezone.utc)),
                )
            pairs: list[dict[str, Any]] = []
            transferred: list[RemoteArtifact] = []
            failures: list[dict[str, Any]] = []
            for source_index, source in enumerate(sources):
                source_path = self._source_path(context, source)
                checksum = compute_source_checksum(source, context.output_dir or context.staging_dir)
                source_identity = stable_artifact_identity(source)
                name = self.target_naming(source)
                if not isinstance(name, str) or not name or Path(name).name != name:
                    raise ValueError("target naming strategy must return a safe basename")
                for destination_index, destination in enumerate(destinations):
                    evidence_target = _join(destination, name)
                    live_target = _join_live(destination, name)
                    request_id = hashlib.sha256(
                        json.dumps(
                            {"source": source_identity, "checksum": checksum, "target": evidence_target},
                            sort_keys=True,
                        ).encode()
                    ).hexdigest()
                    state_key = f"{source_identity}|{checksum}|{evidence_target}"
                    record = prior.get(state_key, {})
                    if record.get("request_id") == request_id and record.get("status") == "succeeded":
                        pairs.append(
                            {
                                "source": source_identity,
                                "source_checksum": checksum,
                                "destination": evidence_target,
                                "request_id": request_id,
                                "replay_identity": request_id,
                                "status": "skipped",
                            }
                        )
                        evidence = _remote_evidence(evidence_target, source.artifact_type)
                        if evidence is not None:
                            transferred.append(evidence)
                        continue
                    error = None
                    attempt = 0
                    while attempt <= self.config.max_retries:
                        attempt += 1
                        try:
                            # Credentials and signed query material are used
                            # only on this live backend call.
                            get_transfer(destination).put(source_path, live_target)
                            error = None
                            break
                        except Exception as exc:  # noqa: BLE001 - backend boundary
                            error = _redact(exc, destinations, (live_target,))
                    if error is None:
                        pair = {
                            "source": source_identity,
                            "source_checksum": checksum,
                            "destination": evidence_target,
                            "request_id": request_id,
                            "replay_identity": request_id,
                            "status": "succeeded",
                            "attempts": attempt,
                        }
                        pairs.append(pair)
                        update = {
                            "request_id": request_id,
                            "replay_identity": request_id,
                            "status": "succeeded",
                        }
                        self._state_updates[state_key] = update
                        prior[state_key] = update
                        self._write_state(state_path, prior)
                        evidence = _remote_evidence(evidence_target, source.artifact_type)
                        if evidence is not None:
                            transferred.append(evidence)
                    else:
                        pair = {
                            "source": source_identity,
                            "source_checksum": checksum,
                            "destination": evidence_target,
                            "request_id": request_id,
                            "replay_identity": request_id,
                            "status": "failed",
                            "attempts": attempt,
                            "error": error,
                        }
                        pairs.append(pair)
                        failures.append(pair)
                        if self.config.failure_policy == PostprocessFailurePolicy.FAIL_FAST:
                            for skipped_destination in destinations[destination_index + 1:]:
                                pairs.append(
                                    {
                                        "source": source_identity,
                                        "source_checksum": checksum,
                                        "destination": _join(skipped_destination, name),
                                        "status": "unattempted",
                                    }
                                )
                            for skipped_source in sources[source_index + 1:]:
                                skipped_name = self.target_naming(skipped_source)
                                skipped_checksum = compute_source_checksum(
                                    skipped_source, context.output_dir or context.staging_dir
                                )
                                for skipped_destination in destinations:
                                    pairs.append(
                                        {
                                            "source": stable_artifact_identity(skipped_source),
                                            "source_checksum": skipped_checksum,
                                            "destination": _join(skipped_destination, skipped_name),
                                            "status": "unattempted",
                                        }
                                    )
                            break
                if failures and self.config.failure_policy == PostprocessFailurePolicy.FAIL_FAST:
                    break
            metadata = {
                "transfer": {
                    "pairs": pairs,
                    "state_namespace": self.config.state_namespace,
                    "replayed_pairs": sum(item["status"] == "skipped" for item in pairs),
                }
            }
            timing = TimingInfo(start_time=start, end_time=datetime.now(timezone.utc))
            if failures:
                return PostprocessFailure(
                    run_id=context.run_result.run_id,
                    error=f"{len(failures)} transfer pair(s) failed",
                    output_dir=str(context.output_dir) if context.output_dir else None,
                    artifacts=list(context.artifacts) + transferred,
                    expected_outputs=list(context.expected_outputs),
                    missing_outputs=list(context.missing_outputs),
                    metadata=metadata,
                    timing=timing,
                )
            return PostprocessSuccess(
                run_id=context.run_result.run_id,
                output_dir=str(context.output_dir or ""),
                validated=True,
                artifacts=list(context.artifacts) + transferred,
                expected_outputs=list(context.expected_outputs),
                missing_outputs=list(context.missing_outputs),
                file_count=len(sources),
                metadata=metadata,
                timing=timing,
            )
        finally:
            if lock is not None:
                try:
                    lock.unlink()
                except FileNotFoundError:
                    pass

    def process_legacy(self, run_result, **kwargs):
        """Explicit adapter for standalone ``ModelRun.postprocess`` calls."""
        context = PostprocessContext.from_run_result(run_result, **kwargs)
        return self.process(context)


__all__ = ["TransferPostprocessor", "TransferPostprocessorConfig", "normalize_destination"]
