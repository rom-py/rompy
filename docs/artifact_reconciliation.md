# Artifact reconciliation

`rompy.core.artifacts.reconcile_artifacts` reconciles only the canonical
`LocalArtifact` and `RemoteArtifact` return-schema identities. It does not
name outputs, transfer files, or inspect model-specific conventions.

```python
from rompy.core.artifacts import reconcile_artifacts
from rompy.core.responses import ArtifactType

reconciled = reconcile_artifacts(
    expected, observed, workspace=run_workspace,
    artifact_types={ArtifactType.NETCDF, ArtifactType.PLOT},
)
```

Local identities are normalized relative to `workspace`; remote URIs remain
remote identities. Workspace escapes (including symlink escapes) are rejected.
Exact duplicate identities are collapsed in stable identity order. Contradictory
metadata for one identity raises `ArtifactConflictError`. `missing` is kept
separate from `observed`, while the type-filter view is exposed as `selected`
and `skipped`; `invalid` and explicitly supplied `conflicting` evidence remain
separate as well.

`compute_source_checksum` streams a local file with SHA-256. Core does not
fetch remote sources: for a remote URI it computes a deterministic checksum of
the canonical URI token. `fingerprint_artifact` returns this checksum together
with a stable identity and stable ID.

A `PostprocessContext` exposes the same operation as
`context.reconcile_artifacts()`. This is a protocol helper only; no ordered
runner, transfer implementation, naming policy, or model-specific discovery
is provided here.
