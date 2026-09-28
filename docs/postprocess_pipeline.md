# Ordered postprocessing and plugin conformance

The postprocessing boundary is an ordered list of independently discovered
steps. Configuration entries are loaded from the canonical
`rompy.postprocess.config` entry-point group:

```yaml
failure_policy: continue
steps:
  - type: noop
    validate_outputs: true
  - type: transfer
    destinations: [file:///tmp/archive]
    artifact_types: [netcdf]
```

`PostprocessPipelineConfig` resolves each step through the same discovery path
as a standalone processor. `run_postprocess_pipeline` gives every context-aware
step an immutable `PostprocessContext`; legacy single processors are adapted by
passing their validated `ModelRunResult`. Artifact evidence is typed and handed
off in order.

`FAIL_FAST` records remaining steps as `unattempted`. `CONTINUE` attempts later
steps and records every failure. The final result metadata contains
`postprocess_pipeline.steps`, `primary_error`, and `secondary_errors` where
applicable. The runner alone validates and writes one canonical
`postprocess_result.json`; plugins must never create a result sidecar.

## Plugin author contract (#17)

A plugin provides a config class with `build_processor()` and a runtime object
with `name` and `process(context)`. Runtime code should use
`context.reconcile_artifacts()`, return a concrete `PostprocessSuccess` or
`PostprocessFailure`, and use namespaced immutable state through
`context.namespace()`/`context.with_state()`. It must not mutate context, write
canonical sidecars, or persist credentials. Plugin projects can use
`rompy.postprocess.conformance.assert_step_conforms` in their own tests.

The built-in transfer processor (#16) is model-neutral: it filters canonical
artifacts, computes an explicit source checksum for every pair, and records a
redacted replay identity. Signed destination URLs are retained only for the
live transfer call; userinfo, query strings, and fragments are absent from
metadata, diagnostics, replay keys, and incremental state. Successful pairs
are persisted under a validated one-component namespace below
`.rompy-postprocess`, so a fresh retry skips them without duplicate uploads or
count inflation. The processor defaults to the source basename and keeps
model-specific naming injectable outside core. These contracts are part of
the composable postprocessing epic (#12, #15, #16, #17); no WW3 or Zarr
integration is included.
