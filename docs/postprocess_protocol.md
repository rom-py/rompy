# Postprocessor protocol

ROMPy exposes a typed contract for postprocessing and an ordered composition
runtime. Import `PostprocessContext`, `PostprocessStep`, and
`PostprocessProcessor` from `rompy.postprocess`.

```python
from datetime import datetime, timezone

from rompy.core.responses import (
    ArtifactType,
    LocalArtifact,
    PostprocessSuccess,
    TimingInfo,
)
from rompy.postprocess import PostprocessContext

class CheckStep:
    name = "check"
    input_protocol = "context"  # explicit capability dispatch

    def process(self, context: PostprocessContext) -> PostprocessSuccess:
        now = datetime.now(timezone.utc)
        artifact = LocalArtifact(path="checked.txt", artifact_type=ArtifactType.TEXT)
        return PostprocessSuccess(
            run_id=context.run_result.run_id,
            output_dir=str(context.output_dir or ""),
            validated=True,
            artifacts=list(context.artifacts) + [artifact],
            expected_outputs=list(context.expected_outputs),
            missing_outputs=list(context.missing_outputs),
            file_count=1,
            message="checked outputs",
            timing=TimingInfo(start_time=now, end_time=datetime.now(timezone.utc)),
        )
```

A standalone processor receives the typed result through the same public seam:

```python
result = model_run.postprocess(config, processor_input=run_result)
```

`processor_input` is a concrete `ModelRunSuccess` or `ModelRunFailure`, and
all v2 result constructors require `run_id`, typed artifact evidence, and
`TimingInfo`. Use `model_dump(mode="json")` for Pydantic v2 serialization.

A context contains one concrete `ModelRunSuccess` or `ModelRunFailure`,
observed artifact evidence, separate expected/missing evidence, a failure
policy, and namespaced operational state. `context.handoff(result)` validates
the concrete result and carries its observed artifacts to the next context.
`PostprocessPipelineConfig` and `run_postprocess_pipeline` provide ordered
composition while keeping this typed handoff contract small.

## Ownership rules

- The core runner owns ordered execution, failure policy, final result
  construction, validation, and the sole canonical
  `postprocess_result.json` sidecar.
- Steps own transformations and integrations only. They must not write a
  competing result sidecar. Artifacts returned by a step are evidence for the
  core handoff, not persistence instructions.
- Operational state is non-canonical, namespaced by processor, recursively
  JSON-safe, and immutable. The core snapshots caller input; processors read a
  namespace and call `context.with_state(name, values)` to receive a new
  context with that namespace replaced. It is for bounded runtime state, not
  result or artifact authority.
- `FAIL_FAST` records remaining steps as unattempted; `CONTINUE` attempts
  later steps and retains primary/secondary failure evidence.
- A `ModelRunFailure` remains the postprocess pipeline's primary failure. Steps
  may process its typed artifacts to retain diagnostics, but an empty pipeline,
  a no-source transfer, or a later successful step still yields
  `PostprocessFailure` and a non-success canonical sidecar. The original run
  error is kept in `postprocess_pipeline.primary_error`; step diagnostics are
  recorded as secondary evidence.

## Configuration discovery

Validated processor configurations are discovered only from the
`rompy.postprocess.config` entry-point group. The sibling
`rompy.postprocess` group is for runtime implementations and is not a config
registry. Discovery is sorted and rejects duplicate names with a deterministic
ambiguity error rather than choosing metadata enumeration order. Existing
`NoopPostprocessorConfig` and single-processor `ModelRun.postprocess(...)`
calls remain supported.
