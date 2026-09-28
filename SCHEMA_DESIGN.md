# Canonical return-schema design

**Status:** Contract authority for issue #3; runtime implementation follows in
#4 and #5.  Executable fixtures and frozen hashes belong to #6.

The detailed normative contract is in
`openspec/changes/implement-return-schemas/`.  This document is a concise API
index for readers of the public documentation and intentionally contains no
alternate API proposal.

## Public result unions

All operation results are typed discriminated unions using `success`:

- `GenerateResult = GenerateSuccess | GenerateFailure`;
- `ModelRunResult = ModelRunSuccess | ModelRunFailure`;
- `PostprocessResult = PostprocessSuccess | PostprocessFailure`; and
- `PipelineResult = PipelineSuccess | PipelineFailure`.

The approved execution boundary is:

```python
result: ModelRunResult = model_run.run(
    backend=backend_config,
    workspace_dir=workspace_dir,
)
```

Consumers branch on `result.success`; they do not infer state from optional
fields.  A result union is a typing alias, not a model class.  For explicit
Pydantic deserialization, use a concrete envelope loader or a `TypeAdapter`:

```python
from pydantic import TypeAdapter
from rompy.core.responses import PipelineResult

result = TypeAdapter(PipelineResult).validate_python(raw_result)
```

## Shared invariants and fields

`TimingInfo` requires timezone-aware UTC `start_time` and `end_time`, with
`end_time >= start_time`; `duration_seconds` is derived numeric seconds.  JSON
wire values for durations, intervals, and stage durations are numbers, never
human-readable strings.

Each variant carries a discriminator and required execution identity.  The
required fields are:

| Variant | Required fields |
|---|---|
| `GenerateSuccess` | `success=true`, `run_id`, `staging_dir`, `generated_files`, `timing` |
| `GenerateFailure` | `success=false`, `run_id`, `error`, `generated_files`, `timing` |
| `ModelRunSuccess` | `success=true`, `run_id`, `backend_used`, `output_dir`, `timing`, `artifacts`, `expected_outputs`, `missing_outputs` |
| `ModelRunFailure` | `success=false`, `run_id`, `backend_used`, `error`, `timing`, `artifacts`, `expected_outputs`, `missing_outputs` |
| `PostprocessSuccess` | `success=true`, `run_id`, `output_dir`, `validated`, `timing`, `artifacts`, `expected_outputs`, `missing_outputs` |
| `PostprocessFailure` | `success=false`, `run_id`, `error`, `timing`, `artifacts`, `expected_outputs`, `missing_outputs` |
| `PipelineSuccess` | `success=true`, `run_id`, exact stages, `backend`, `processor`, `staging_dir`, `output_dir`, nested `PostprocessSuccess`, `timing`, `stage_timings` |
| `PipelineFailure` | `success=false`, `run_id`, strict successful prefix, `backend`, `processor`, `failed_stage`, `error`, `timing`, `stage_timings`, `cleaned_up` |

Known output/workspace paths are optional on failure. `workspace_dir`, messages,
file counts, and JSON-safe `metadata` are optional where not listed as required.
A failed pipeline carries nested `PostprocessFailure` when
`failed_stage == POSTPROCESS`; its own timing and evidence are retained.
`failed_stage` is never included in `stages_completed`.

A persistence diagnostic is optional except when persistence fails. Its exact
shape is:

```json
{
  "status": "failed",
  "sidecar_kind": "run_result",
  "sidecar_path": "staging/run-42/run_result.json",
  "error": "permission denied",
  "primary_error": null
}
```

`primary_error` preserves the original operation error when both operation and
persistence fail. A result is not reported as canonical success if its required
sidecar cannot be persisted.

## Artifact and validation evidence

`artifacts` contains observed outputs only. Each identity is one of:

```json
[
  {"kind": "local", "path": "outputs/waves.nc"},
  {"kind": "remote", "uri": "s3://bucket/run-42/summary.json"}
]
```

Local paths are normalized staging-relative POSIX paths and cannot be absolute,
traversal, or URI-like. Remote artifacts are explicit URI variants and are not
interpreted as local paths. `expected_outputs` and `missing_outputs` are
separate structured evidence; missing expected outputs are not filtered out
because they are absent from the current filesystem.

## Processor and pipeline boundaries

Processors are built from one validated postprocessor configuration path and
receive the same unchanged validated `ModelRunResult` in direct Python, local
pipeline, CLI, and fresh-process paths. Their return is validated immediately
as `PostprocessSuccess | PostprocessFailure`; dictionaries, `None`, and malformed
union states are rejected.

Pipeline stages are `GENERATE -> RUN -> POSTPROCESS`. Success has all three.
Failures have strict prefixes: `[]`, `[GENERATE]`, or `[GENERATE, RUN]` for
failure at generate, run, or postprocess. Cleanup is true only after confirmed
cleanup and cannot hide the stage's primary error.

## Sidecar and compatibility policy

Canonical sidecars are `generate_result.json`, `run_result.json`, and
`postprocess_result.json`, each with current integer `schema_version: 2` and
matching envelope/payload `kind`, `run_id`, `status`, and `success`. Loaders
reject missing, boolean, unsupported, mixed, core-v1, and flat WW3-v1 versions
with actionable kind/version errors. No migration reader is included in #3.

## Ownership and validation

#4 implements validators, adapters, round trips, and persistence failure
behavior. #5 implements processor and execution-path parity. #6 executes the
bounded JSON examples, freezes executable success/failure/malformed/legacy
fixtures, and publishes hashes after #4/#5 implement the contract.
