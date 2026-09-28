"""Contract tests for model-neutral artifact reconciliation."""

from pathlib import Path

import pytest

from rompy.core.artifacts import (
    ArtifactConflictError,
    ArtifactPathError,
    compute_source_checksum,
    fingerprint_artifact,
    reconcile_artifacts,
    stable_artifact_identity,
)
from rompy.core.responses import ArtifactType, LocalArtifact, RemoteArtifact


def test_reconcile_normalizes_deduplicates_and_filters(tmp_path: Path):
    (tmp_path / "outputs").mkdir()
    expected = LocalArtifact(path="outputs/result.nc", artifact_type=ArtifactType.NETCDF)
    remote = RemoteArtifact(uri="s3://bucket/result.nc", artifact_type=ArtifactType.NETCDF)
    result = reconcile_artifacts(
        [expected, expected],
        [expected, expected, remote],
        workspace=tmp_path,
        artifact_types=ArtifactType.NETCDF,
    )

    assert [stable_artifact_identity(item) for item in result.expected] == [
        "local:outputs/result.nc"
    ]
    assert len(result.observed) == 2
    assert len(result.selected) == 2
    assert result.missing == []
    assert result.skipped == []

    text = LocalArtifact(path="outputs/result.txt", artifact_type=ArtifactType.TEXT)
    filtered = reconcile_artifacts([expected], [expected, text], workspace=tmp_path, artifact_types=ArtifactType.NETCDF)
    assert filtered.selected == [expected]
    assert filtered.skipped == [text]


def test_reconcile_preserves_missing_and_explicit_evidence(tmp_path: Path):
    expected = LocalArtifact(path="expected.nc", artifact_type=ArtifactType.NETCDF)
    observed = LocalArtifact(path="other.nc", artifact_type=ArtifactType.NETCDF)
    invalid = RemoteArtifact(uri="https://example.invalid/bad", artifact_type=ArtifactType.OTHER)
    result = reconcile_artifacts(
        [expected], [observed], workspace=tmp_path, invalid=[invalid]
    )
    assert result.missing == [expected]
    assert result.observed == [observed]
    assert result.invalid == [invalid]


def test_contradictory_duplicate_is_rejected():
    with pytest.raises(ArtifactConflictError, match="contradictory"):
        reconcile_artifacts(
            [LocalArtifact(path="result.nc", artifact_type=ArtifactType.NETCDF)],
            [
                LocalArtifact(path="result.nc", artifact_type=ArtifactType.NETCDF, size_bytes=1),
                LocalArtifact(path="result.nc", artifact_type=ArtifactType.NETCDF, size_bytes=2),
            ],
        )


def test_path_safety_and_source_fingerprints(tmp_path: Path):
    (tmp_path / "safe.nc").write_bytes(b"rompy")
    assert compute_source_checksum(LocalArtifact(path="safe.nc"), tmp_path) == (
        "e56f6cfee7a48f1c9d444b8deba3abfb834b886419cf70c6f20f2d3363c19d8f"
    )
    fingerprint = fingerprint_artifact(LocalArtifact(path="safe.nc"), tmp_path)
    assert fingerprint.identity == "local:safe.nc"
    assert len(fingerprint.stable_id) == 64
    assert len(fingerprint.source_checksum or "") == 64

    remote = fingerprint_artifact(RemoteArtifact(uri="https://example.test/a"))
    assert remote.identity == "remote:https://example.test/a"
    with pytest.raises(ValueError):
        reconcile_artifacts([LocalArtifact(path="../outside.nc")], [], workspace=tmp_path)

    outside = tmp_path.parent / "rompy-artifact-outside"
    outside.mkdir(exist_ok=True)
    (outside / "escape.nc").write_bytes(b"outside")
    (tmp_path / "link").symlink_to(outside, target_is_directory=True)
    with pytest.raises(ArtifactPathError, match="escapes workspace"):
        reconcile_artifacts([LocalArtifact(path="link/escape.nc")], [], workspace=tmp_path)
