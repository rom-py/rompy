"""Strict canonical sidecar serialization and durable atomic persistence."""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel, TypeAdapter

from rompy.core.responses import (
    ArtifactIdentity,
    GenerateFailure,
    GenerateResultSidecar,
    GenerateSuccess,
    ModelRunFailure,
    ModelRunSuccess,
    PersistenceDiagnostic,
    PostprocessFailure,
    PostprocessResultSidecar,
    PostprocessSuccess,
    RunResultSidecar,
    TimingInfo,
)

GENERATE_RESULT_FILENAME = "generate_result.json"
RUN_RESULT_FILENAME = "run_result.json"
POSTPROCESS_RESULT_FILENAME = "postprocess_result.json"

T = TypeVar("T", bound=BaseModel)


def _atomic_write(path: Path, data: bytes) -> None:
    """Write ``data`` with same-directory temp + replace and fsync barriers.

    A failed write, replace, or sync never removes an existing destination and
    always attempts to remove its temporary file.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, str(path))
        directory_fd = os.open(str(path.parent), os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        if os.path.exists(temporary):
            try:
                os.unlink(temporary)
            except OSError:
                pass


def _serialized(model: BaseModel) -> bytes:
    # model_dump(mode="json") preserves numeric duration fields and emits RFC
    # 3339 timestamps. sort_keys gives deterministic repeated writes.
    value = model.model_dump(mode="json")
    return (json.dumps(
        value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False
    ) + "\n").encode(
        "utf-8"
    )


def _write(staging_dir: Path, filename: str, sidecar: BaseModel) -> Path:
    destination = Path(staging_dir) / filename
    _atomic_write(destination, _serialized(sidecar))
    return destination


def write_generate_result(staging_dir: Path, sidecar: GenerateResultSidecar) -> Path:
    return _write(staging_dir, GENERATE_RESULT_FILENAME, sidecar)


def write_run_result(staging_dir: Path, sidecar: RunResultSidecar) -> Path:
    return _write(staging_dir, RUN_RESULT_FILENAME, sidecar)


def write_postprocess_result(
    staging_dir: Path, sidecar: PostprocessResultSidecar
) -> Path:
    return _write(staging_dir, POSTPROCESS_RESULT_FILENAME, sidecar)


def _load(
    path_or_dir: Path,
    filename: str,
    kind: str,
    model: type[T],
) -> T:
    path = Path(path_or_dir)
    if path.is_dir():
        path = path / filename
    if not path.exists():
        raise FileNotFoundError(f"{kind} sidecar not found: {path}\nExpected file: {filename}")
    try:
        raw: Any = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Invalid JSON in {path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise ValueError(f"Canonical {kind} sidecar must be a JSON object: {path}")  # noqa: TRY004
    observed_kind = raw.get("kind")
    if observed_kind != kind:
        raise ValueError(
            f"Invalid kind {observed_kind!r} in {path}; expected {kind!r}. "
            "Regenerate a canonical sidecar."
        )
    version = raw.get("schema_version")
    if isinstance(version, bool) or not isinstance(version, int) or version != 2:
        raise ValueError(
            f"Unsupported schema_version {version!r} in {path}; expected integer 2. "
            "Regenerate a canonical sidecar."
        )
    try:
        return model.model_validate(raw)
    except Exception as exc:
        raise ValueError(f"Invalid canonical {kind} sidecar {path}: {exc}") from exc


def _safe_metadata(value: Any) -> dict[str, Any]:
    """Copy JSON-safe metadata, dropping mutated invalid mappings."""
    if not isinstance(value, dict):
        return {}
    try:
        return json.loads(json.dumps(value, allow_nan=False))
    except (TypeError, ValueError, OverflowError):
        return {}


def _safe_strings(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _safe_optional_string(value: Any) -> str | None:
    return value if isinstance(value, str) else None


def _safe_required_string(value: Any, default: str = "unknown") -> str:
    return value if isinstance(value, str) and value.strip() else default


def _safe_timing(value: Any) -> TimingInfo:
    try:
        raw = value.model_dump(mode="python")
        return TimingInfo.model_validate(raw)
    except Exception:  # noqa: BLE001 - fallback must not rethrow persistence errors
        now = datetime.now(timezone.utc)
        return TimingInfo(start_time=now, end_time=now)


def _safe_evidence(value: Any) -> list[Any]:
    if not isinstance(value, list):
        return []
    adapter = TypeAdapter(ArtifactIdentity)
    valid = []
    for item in value:
        try:
            raw = item.model_dump(mode="python") if isinstance(item, BaseModel) else item
            valid.append(adapter.validate_python(raw))
        except Exception:  # noqa: BLE001, S112 - invalid mutable evidence is dropped
            continue
    return valid


def _failure_with_diagnostic(result: Any, diagnostic: PersistenceDiagnostic, primary_error: str | None) -> Any:
    """Return the corresponding typed failure after persistence fails.

    Result instances may have been mutated after Pydantic validation. Every
    mutable value copied into the fallback is therefore normalized or dropped
    before constructing the typed failure.
    """
    operation_error = primary_error or getattr(result, "error", None)
    metadata = _safe_metadata(getattr(result, "metadata", {}))
    timing = _safe_timing(getattr(result, "timing", None))
    error = _safe_required_string(operation_error, diagnostic.error)
    run_id = _safe_required_string(getattr(result, "run_id", None))
    if isinstance(result, GenerateSuccess):
        return GenerateFailure(
            run_id=run_id,
            error=error,
            generated_files=_safe_strings(getattr(result, "generated_files", [])),
            timing=timing,
            staging_dir=_safe_required_string(getattr(result, "staging_dir", None), "staging"),
            config_file=_safe_optional_string(getattr(result, "config_file", None)),
            metadata=metadata,
            persistence_diagnostic=diagnostic,
        )
    if isinstance(result, ModelRunSuccess):
        return ModelRunFailure(
            run_id=run_id,
            backend_used=_safe_required_string(getattr(result, "backend_used", None)),
            error=error,
            timing=timing,
            output_dir=_safe_optional_string(getattr(result, "output_dir", None)),
            workspace_dir=_safe_optional_string(getattr(result, "workspace_dir", None)),
            artifacts=_safe_evidence(getattr(result, "artifacts", [])),
            expected_outputs=_safe_evidence(getattr(result, "expected_outputs", [])),
            missing_outputs=_safe_evidence(getattr(result, "missing_outputs", [])),
            message=_safe_optional_string(getattr(result, "message", None)),
            metadata=metadata,
            persistence_diagnostic=diagnostic,
        )
    if isinstance(result, PostprocessSuccess):
        return PostprocessFailure(
            run_id=run_id,
            error=error,
            timing=timing,
            output_dir=_safe_optional_string(getattr(result, "output_dir", None)),
            artifacts=_safe_evidence(getattr(result, "artifacts", [])),
            expected_outputs=_safe_evidence(getattr(result, "expected_outputs", [])),
            missing_outputs=_safe_evidence(getattr(result, "missing_outputs", [])),
            message=_safe_optional_string(getattr(result, "message", None)),
            metadata=metadata,
            persistence_diagnostic=diagnostic,
        )
    if isinstance(result, GenerateFailure):
        return result.model_copy(
            update={
                "run_id": run_id,
                "error": error,
                "generated_files": _safe_strings(getattr(result, "generated_files", [])),
                "timing": timing,
                "staging_dir": _safe_optional_string(getattr(result, "staging_dir", None)),
                "config_file": _safe_optional_string(getattr(result, "config_file", None)),
                "metadata": metadata,
                "persistence_diagnostic": diagnostic,
            }
        )
    if isinstance(result, ModelRunFailure):
        return result.model_copy(
            update={
                "run_id": run_id,
                "error": error,
                "timing": timing,
                "backend_used": _safe_required_string(getattr(result, "backend_used", None)),
                "output_dir": _safe_optional_string(getattr(result, "output_dir", None)),
                "workspace_dir": _safe_optional_string(getattr(result, "workspace_dir", None)),
                "artifacts": _safe_evidence(getattr(result, "artifacts", [])),
                "expected_outputs": _safe_evidence(getattr(result, "expected_outputs", [])),
                "missing_outputs": _safe_evidence(getattr(result, "missing_outputs", [])),
                "message": _safe_optional_string(getattr(result, "message", None)),
                "metadata": metadata,
                "persistence_diagnostic": diagnostic,
            }
        )
    if isinstance(result, PostprocessFailure):
        return result.model_copy(
            update={
                "run_id": run_id,
                "error": error,
                "timing": timing,
                "output_dir": _safe_optional_string(getattr(result, "output_dir", None)),
                "artifacts": _safe_evidence(getattr(result, "artifacts", [])),
                "expected_outputs": _safe_evidence(getattr(result, "expected_outputs", [])),
                "missing_outputs": _safe_evidence(getattr(result, "missing_outputs", [])),
                "message": _safe_optional_string(getattr(result, "message", None)),
                "metadata": metadata,
                "persistence_diagnostic": diagnostic,
            }
        )
    raise TypeError(
        "persist_result supports Generate, ModelRun, and Postprocess result variants"
    )


def persist_result(
    result: Any,
    sidecar: GenerateResultSidecar | RunResultSidecar | PostprocessResultSidecar,
    staging_dir: Path,
    *,
    primary_error: str | None = None,
) -> Any:
    """Persist a result and turn any persistence error into typed failure evidence.

    This adapter is intentionally a core seam: operation producers can adopt it
    without duplicating error handling. Existing producer call sites remain a
    downstream integration concern. Serialization, temporary-file, file-sync,
    replace, and directory-sync failures are all reported in the returned
    ``PersistenceDiagnostic``; no exception from persistence masks a supplied
    primary operation error.
    """
    writers = {
        GenerateResultSidecar: write_generate_result,
        RunResultSidecar: write_run_result,
        PostprocessResultSidecar: write_postprocess_result,
    }
    writer = writers.get(type(sidecar))
    if writer is None:
        raise TypeError(f"unsupported canonical sidecar type: {type(sidecar).__name__}")
    sidecar_path = Path(staging_dir) / {
        GenerateResultSidecar: GENERATE_RESULT_FILENAME,
        RunResultSidecar: RUN_RESULT_FILENAME,
        PostprocessResultSidecar: POSTPROCESS_RESULT_FILENAME,
    }[type(sidecar)]
    try:
        writer(staging_dir, sidecar)
    except Exception as exc:  # noqa: BLE001 - persistence must be observable
        raw_primary_error = primary_error
        if raw_primary_error is None:
            raw_primary_error = getattr(result, "error", None)
        safe_primary_error = (
            _safe_required_string(raw_primary_error)
            if isinstance(raw_primary_error, str)
            else None
        )
        diagnostic = PersistenceDiagnostic(
            sidecar_kind=sidecar.kind,
            sidecar_path=str(sidecar_path),
            error=_safe_required_string(str(exc), "result persistence failed"),
            primary_error=safe_primary_error,
        )
        return _failure_with_diagnostic(result, diagnostic, safe_primary_error)
    return result


def load_generate_result(path_or_dir: Path) -> GenerateResultSidecar:
    return _load(path_or_dir, GENERATE_RESULT_FILENAME, "generate_result", GenerateResultSidecar)


def load_run_result(path_or_dir: Path) -> RunResultSidecar:
    return _load(path_or_dir, RUN_RESULT_FILENAME, "run_result", RunResultSidecar)


def load_postprocess_result(path_or_dir: Path) -> PostprocessResultSidecar:
    return _load(
        path_or_dir,
        POSTPROCESS_RESULT_FILENAME,
        "postprocess_result",
        PostprocessResultSidecar,
    )