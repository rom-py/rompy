"""Model-neutral artifact identity and reconciliation helpers.

The functions in this module operate on the canonical local/remote artifact
variants from :mod:`rompy.core.responses`.  They intentionally do not know
about model naming, transfer destinations, or model-specific artifact kinds.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
import hashlib
import json
from pathlib import Path
from pydantic import Field, TypeAdapter

from rompy.core.responses import (
    ArtifactIdentity,
    ArtifactType,
    LocalArtifact,
    RemoteArtifact,
)
from rompy.core.types import RompyBaseModel


class ArtifactPathError(ValueError):
    """Raised when an artifact cannot be contained by its workspace."""


class ArtifactConflictError(ValueError):
    """Raised when one identity is described by contradictory evidence."""

    def __init__(self, identity: str, artifacts: Sequence[ArtifactIdentity]):
        self.identity = identity
        self.artifacts = tuple(artifacts)
        super().__init__(
            f"contradictory artifact evidence for {identity!r}: "
            f"{len(self.artifacts)} variants"
        )


class ArtifactFingerprint(RompyBaseModel):
    """Deterministic identity and optional content checksum for one artifact."""

    identity: str
    stable_id: str
    source_checksum: str | None = None


class ArtifactReconciliation(RompyBaseModel):
    """The complete, model-neutral artifact evidence set.

    ``observed`` and ``missing`` are deliberately separate.  ``selected`` and
    ``skipped`` are a deterministic type-filter view of observed evidence;
    neither changes the declared expected or missing evidence.
    """

    expected: list[ArtifactIdentity] = Field(default_factory=list)
    observed: list[ArtifactIdentity] = Field(default_factory=list)
    missing: list[ArtifactIdentity] = Field(default_factory=list)
    selected: list[ArtifactIdentity] = Field(default_factory=list)
    skipped: list[ArtifactIdentity] = Field(default_factory=list)
    invalid: list[ArtifactIdentity] = Field(default_factory=list)
    conflicting: list[ArtifactIdentity] = Field(default_factory=list)

    @property
    def expected_outputs(self) -> list[ArtifactIdentity]:
        """Compatibility spelling used by the return-schema responses."""
        return self.expected

    @property
    def observed_outputs(self) -> list[ArtifactIdentity]:
        return self.observed

    @property
    def missing_outputs(self) -> list[ArtifactIdentity]:
        return self.missing


_ARTIFACT_ADAPTER = TypeAdapter(ArtifactIdentity)


def _typed(items: Iterable[ArtifactIdentity], field: str) -> list[ArtifactIdentity]:
    result: list[ArtifactIdentity] = []
    for item in items:
        try:
            value = _ARTIFACT_ADAPTER.validate_python(item)
        except Exception as exc:  # pydantic supplies the useful contract detail
            raise TypeError(f"{field} must contain typed ArtifactIdentity values") from exc
        result.append(value)
    return result


def _workspace_path(workspace: Path | str) -> Path:
    path = Path(workspace).expanduser().resolve(strict=False)
    if not path.exists() and path != path.parent:
        # The workspace is allowed to be created by a later execution stage.
        return path
    if not path.is_dir():
        raise ArtifactPathError(f"workspace is not a directory: {path}")
    return path


def normalize_artifact(
    artifact: ArtifactIdentity, workspace: Path | str | None = None
) -> ArtifactIdentity:
    """Normalize a local identity relative to ``workspace``.

    Remote URIs are never interpreted as paths.  Local paths are resolved
    against the workspace (including existing symlinks), then validated again
    by the canonical typed artifact contract.
    """
    value = _ARTIFACT_ADAPTER.validate_python(artifact)
    if not isinstance(value, LocalArtifact) or workspace is None:
        return value

    root = _workspace_path(workspace)
    candidate = (root / value.path).resolve(strict=False)
    try:
        relative = candidate.relative_to(root).as_posix()
    except ValueError as exc:
        raise ArtifactPathError(
            f"local artifact escapes workspace {root}: {value.path!r}"
        ) from exc
    if not relative or relative == ".":
        raise ArtifactPathError("local artifact path must identify a workspace entry")
    try:
        return value.model_copy(update={"path": relative})
    except Exception as exc:
        raise ArtifactPathError(f"invalid normalized local artifact path: {relative!r}") from exc


def stable_artifact_identity(artifact: ArtifactIdentity) -> str:
    """Return a stable, human-readable identity independent of metadata."""
    value = _ARTIFACT_ADAPTER.validate_python(artifact)
    if isinstance(value, LocalArtifact):
        return f"local:{value.path}"
    return f"remote:{value.uri}"


def artifact_stable_id(artifact: ArtifactIdentity) -> str:
    """Return a compact deterministic ID for an artifact identity."""
    identity = stable_artifact_identity(artifact)
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()


def compute_source_checksum(
    artifact: ArtifactIdentity, workspace: Path | str | None = None
) -> str:
    """Compute a generic SHA-256 source checksum.

    Local checksums are streamed from the workspace file.  A remote source is
    not fetched by core, so its canonical URI is checksummed as a stable
    source token instead.  Transfer execution remains outside this module.
    """
    value = normalize_artifact(artifact, workspace)
    digest = hashlib.sha256()
    if isinstance(value, RemoteArtifact):
        digest.update(value.uri.encode("utf-8"))
        return digest.hexdigest()
    if workspace is None:
        raise ArtifactPathError("workspace is required to checksum a local artifact")
    path = _workspace_path(workspace) / value.path
    if not path.is_file():
        raise ArtifactPathError(f"local artifact is not a regular file: {path}")
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


# Short aliases for callers using the nouns from the issue description.
source_checksum = compute_source_checksum
artifact_identity = stable_artifact_identity


def fingerprint_artifact(
    artifact: ArtifactIdentity, workspace: Path | str | None = None
) -> ArtifactFingerprint:
    """Build a deterministic identity/checksum record without transfer."""
    value = normalize_artifact(artifact, workspace)
    return ArtifactFingerprint(
        identity=stable_artifact_identity(value),
        stable_id=artifact_stable_id(value),
        source_checksum=compute_source_checksum(value, workspace),
    )


def _canonical(
    items: Iterable[ArtifactIdentity],
    *,
    workspace: Path | str | None,
    field: str,
) -> list[ArtifactIdentity]:
    normalized = [normalize_artifact(item, workspace) for item in _typed(items, field)]
    by_identity: dict[str, list[ArtifactIdentity]] = {}
    for item in normalized:
        by_identity.setdefault(stable_artifact_identity(item), []).append(item)

    canonical: list[ArtifactIdentity] = []
    for identity in sorted(by_identity):
        variants = by_identity[identity]
        unique: dict[str, ArtifactIdentity] = {
            json.dumps(item.model_dump(mode="json"), sort_keys=True): item
            for item in variants
        }
        if len(unique) > 1:
            raise ArtifactConflictError(identity, tuple(unique.values()))
        canonical.append(next(iter(unique.values())))
    return canonical


def _allowed_types(
    artifact_types: ArtifactType | Iterable[ArtifactType] | None,
) -> set[ArtifactType] | None:
    if artifact_types is None:
        return None
    if isinstance(artifact_types, ArtifactType):
        return {artifact_types}
    try:
        return {ArtifactType(value) for value in artifact_types}
    except (TypeError, ValueError) as exc:
        raise ValueError("artifact_types must contain ArtifactType values") from exc


def reconcile_artifacts(
    expected: Iterable[ArtifactIdentity],
    observed: Iterable[ArtifactIdentity],
    *,
    workspace: Path | str | None = None,
    missing: Iterable[ArtifactIdentity] | None = None,
    invalid: Iterable[ArtifactIdentity] = (),
    conflicting: Iterable[ArtifactIdentity] = (),
    artifact_types: ArtifactType | Iterable[ArtifactType] | None = None,
) -> ArtifactReconciliation:
    """Reconcile typed expected and observed evidence deterministically.

    Exact duplicates collapse to one canonical item.  Contradictory metadata
    for the same local path or remote URI raises :class:`ArtifactConflictError`.
    The optional evidence collections are accepted only as typed artifacts and
    remain separate from observed/missing evidence.
    """
    expected_values = _canonical(expected, workspace=workspace, field="expected")
    observed_values = _canonical(observed, workspace=workspace, field="observed")
    if missing is None:
        observed_ids = {stable_artifact_identity(item) for item in observed_values}
        missing_values = [
            item
            for item in expected_values
            if stable_artifact_identity(item) not in observed_ids
        ]
    else:
        missing_values = _canonical(missing, workspace=workspace, field="missing")
    invalid_values = _canonical(invalid, workspace=workspace, field="invalid")
    conflicting_values = _canonical(conflicting, workspace=workspace, field="conflicting")

    allowed = _allowed_types(artifact_types)
    if allowed is None:
        selected, skipped = list(observed_values), []
    else:
        selected = [item for item in observed_values if item.artifact_type in allowed]
        skipped = [item for item in observed_values if item.artifact_type not in allowed]

    return ArtifactReconciliation(
        expected=expected_values,
        observed=observed_values,
        missing=missing_values,
        selected=selected,
        skipped=skipped,
        invalid=invalid_values,
        conflicting=conflicting_values,
    )


__all__ = [
    "ArtifactConflictError",
    "ArtifactFingerprint",
    "ArtifactPathError",
    "ArtifactReconciliation",
    "artifact_identity",
    "artifact_stable_id",
    "compute_source_checksum",
    "fingerprint_artifact",
    "normalize_artifact",
    "reconcile_artifacts",
    "source_checksum",
    "stable_artifact_identity",
]
