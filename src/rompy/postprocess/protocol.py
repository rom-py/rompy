"""Typed contracts for composable postprocessing steps.

This module deliberately defines contracts, not a composition runner.  The
core runner remains the only owner of result construction and canonical
``postprocess_result.json`` persistence; a future runner can use these types
without giving a step filesystem or sidecar ownership.
"""

from __future__ import annotations

import math
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field, replace
from enum import Enum
from pathlib import Path
from typing import Protocol, TypeAlias, runtime_checkable

from pydantic import TypeAdapter

from rompy.core.artifacts import ArtifactReconciliation, reconcile_artifacts
from rompy.core.responses import (
    ArtifactIdentity,
    ArtifactType,
    ModelRunFailure,
    ModelRunResult,
    ModelRunSuccess,
    PostprocessFailure,
    PostprocessResult,
    PostprocessSuccess,
)

ModelRunResultValue: TypeAlias = ModelRunSuccess | ModelRunFailure
PostprocessResultValue: TypeAlias = PostprocessSuccess | PostprocessFailure
JSONScalar: TypeAlias = str | int | float | bool | None
JSONValue: TypeAlias = JSONScalar | list["JSONValue"] | dict[str, "JSONValue"]
OperationalState: TypeAlias = Mapping[str, Mapping[str, JSONValue]]


class _ImmutableDict(dict[str, JSONValue]):
    """JSON object snapshot that preserves dict behaviour without mutation."""

    def _immutable(self, *args: object, **kwargs: object) -> None:
        raise TypeError("postprocess operational state is immutable")

    __delitem__ = __setitem__ = clear = pop = popitem = setdefault = update = _immutable
    __ior__ = _immutable


class _ImmutableList(list[JSONValue]):
    """JSON array snapshot that preserves list behaviour without mutation."""

    def _immutable(self, *args: object, **kwargs: object) -> None:
        raise TypeError("postprocess operational state is immutable")

    __delitem__ = __setitem__ = __iadd__ = __imul__ = _immutable
    append = clear = extend = insert = pop = remove = reverse = sort = _immutable


def _validated_json_value(value: object, path: str) -> JSONValue:
    """Validate and recursively snapshot one JSON-compatible value."""
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"operational_state value at {path} must be finite")
        return value
    if isinstance(value, Mapping):
        snapshot: _ImmutableDict = _ImmutableDict()
        for key, nested in value.items():
            if not isinstance(key, str):
                raise ValueError(  # noqa: TRY004 - public JSON validation uses ValueError
                    f"operational_state object key at {path} must be a string"
                )
            dict.__setitem__(
                snapshot, key, _validated_json_value(nested, f"{path}.{key}")
            )
        return snapshot
    if isinstance(value, list):
        snapshot: _ImmutableList = _ImmutableList()
        for index, nested in enumerate(value):
            list.append(snapshot, _validated_json_value(nested, f"{path}[{index}]"))
        return snapshot
    raise ValueError(
        f"operational_state value at {path} is not JSON-safe: {type(value).__name__}"
    )


_SAFE_NAMESPACE = re.compile(r"[A-Za-z0-9_-]+\Z")


def validate_state_namespace(namespace: str) -> str:
    """Validate one filesystem-safe operational-state path component."""
    if not isinstance(namespace, str) or not _SAFE_NAMESPACE.fullmatch(namespace):
        raise ValueError(
            "operational_state state_namespace must be one safe path component "
            "containing only letters, digits, '_' or '-'")
    return namespace


def _snapshot_operational_state(state: object) -> OperationalState:
    """Validate and recursively copy namespaced operational state."""
    if not isinstance(state, Mapping):
        raise ValueError(  # noqa: TRY004 - public JSON validation uses ValueError
            "operational_state must be a mapping of namespaces"
        )
    snapshot: _ImmutableDict = _ImmutableDict()
    for namespace, values in state.items():
        validate_state_namespace(namespace)
        if not isinstance(values, Mapping):
            raise ValueError(  # noqa: TRY004 - public JSON validation uses ValueError
                f"operational_state namespace {namespace!r} must be a mapping"
            )
        validated = _validated_json_value(values, f"namespace {namespace!r}")
        dict.__setitem__(snapshot, namespace, validated)
    return snapshot


class PostprocessFailurePolicy(str, Enum):
    """Policy a future ordered runner applies when a step returns failure."""

    FAIL_FAST = "fail_fast"
    CONTINUE = "continue"


# Short spelling for callers that do not need the postprocess prefix.
FailurePolicy = PostprocessFailurePolicy


@dataclass(frozen=True)
class PostprocessContext:
    """Immutable handoff context owned by the core postprocess runner.

    ``run_result`` is the concrete, validated result from the run stage.  A
    step receives observed artifact evidence in ``artifacts`` plus the
    independent expected/missing evidence.  A future ordered runner creates a
    new context from each validated step result with :meth:`handoff`; steps do
    not mutate or replace another step's evidence.

    ``operational_state`` is an intentionally non-canonical, namespaced,
    recursively immutable JSON-safe mapping.  A processor reads its own
    namespace and uses :meth:`with_state` to request an immutable context with
    updated state; processors do not mutate a context in place.  State is not a
    result sidecar, and processors must not write ``postprocess_result.json``.
    The core runner owns failure handling, final result construction, and the
    one canonical sidecar.
    """

    run_result: ModelRunResultValue
    output_dir: Path | None = None
    staging_dir: Path | None = None
    artifacts: tuple[ArtifactIdentity, ...] = ()
    expected_outputs: tuple[ArtifactIdentity, ...] = ()
    missing_outputs: tuple[ArtifactIdentity, ...] = ()
    failure_policy: PostprocessFailurePolicy = PostprocessFailurePolicy.FAIL_FAST
    operational_state: OperationalState = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate the public boundary and snapshot all mutable inputs."""
        validated_run = TypeAdapter(ModelRunResult).validate_python(self.run_result)
        object.__setattr__(self, "run_result", validated_run)
        adapter = TypeAdapter(ArtifactIdentity)
        for field_name in ("artifacts", "expected_outputs", "missing_outputs"):
            evidence = tuple(
                adapter.validate_python(item) for item in getattr(self, field_name)
            )
            object.__setattr__(self, field_name, evidence)
        if not isinstance(self.failure_policy, PostprocessFailurePolicy):
            object.__setattr__(
                self,
                "failure_policy",
                PostprocessFailurePolicy(self.failure_policy),
            )
        object.__setattr__(
            self, "operational_state", _snapshot_operational_state(self.operational_state)
        )

    @classmethod
    def from_run_result(
        cls,
        run_result: ModelRunResultValue,
        *,
        staging_dir: Path | str | None = None,
        failure_policy: PostprocessFailurePolicy = PostprocessFailurePolicy.FAIL_FAST,
        operational_state: OperationalState | None = None,
    ) -> PostprocessContext:
        """Build initial context from a concrete validated run result.

        Existing run-stage evidence is copied into immutable tuples.  This is
        the only initial handoff needed by a processor; no live ``ModelRun``
        object or path-only substitute is accepted.
        """
        result = TypeAdapter(ModelRunResult).validate_python(run_result)
        return cls(
            run_result=result,
            output_dir=Path(result.output_dir) if result.output_dir else None,
            staging_dir=Path(staging_dir)
            if staging_dir is not None
            else (Path(result.workspace_dir) if result.workspace_dir else None),
            artifacts=tuple(result.artifacts),
            expected_outputs=tuple(result.expected_outputs),
            missing_outputs=tuple(result.missing_outputs),
            failure_policy=failure_policy,
            operational_state=operational_state or {},
        )

    def namespace(self, name: str) -> Mapping[str, JSONValue]:
        """Return one immutable processor-owned operational-state namespace."""
        validate_state_namespace(name)
        return self.operational_state.get(name, _ImmutableDict())

    def with_state(
        self, namespace: str, values: Mapping[str, JSONValue]
    ) -> PostprocessContext:
        """Return a new context with one processor namespace replaced.

        State updates are core-owned and immutable: the supplied mapping is
        validated and copied, and neither this context nor the returned context
        can be changed through the state mapping.  Other namespaces are kept.
        """
        validate_state_namespace(namespace)
        if not isinstance(values, Mapping):
            raise ValueError(  # noqa: TRY004 - public JSON validation uses ValueError
                "operational-state namespace values must be a mapping"
            )
        state = dict(self.operational_state)
        state[namespace] = values
        return replace(self, operational_state=state)

    def reconcile_artifacts(
        self,
        *,
        artifact_types: ArtifactType | Iterable[ArtifactType] | None = None,
    ) -> ArtifactReconciliation:
        """Reconcile this handoff's typed evidence without running a step.

        The context's staging directory is the only workspace authority.  This
        exposes the core reconciliation contract to protocol steps while
        leaving ordered execution and result persistence to the future runner.
        """
        return reconcile_artifacts(
            self.expected_outputs,
            self.artifacts,
            workspace=self.staging_dir,
            missing=self.missing_outputs,
            artifact_types=artifact_types,
        )

    def handoff(self, result: PostprocessResultValue) -> PostprocessContext:
        """Create the next ordered-step context from a concrete step result.

        The core boundary validates the returned discriminated union before
        handoff.  Artifact evidence is replaced by the step's observed
        evidence while expected and missing evidence remain explicit.
        """
        validated = TypeAdapter(PostprocessResult).validate_python(result)
        return replace(
            self,
            output_dir=Path(validated.output_dir)
            if validated.output_dir
            else self.output_dir,
            artifacts=tuple(validated.artifacts),
            expected_outputs=tuple(validated.expected_outputs),
            missing_outputs=tuple(validated.missing_outputs),
            operational_state=dict(self.operational_state),
        )


@runtime_checkable
class PostprocessStep(Protocol):
    """Minimal ordered step contract for a future composition runner."""

    name: str

    def process(self, context: PostprocessContext) -> PostprocessResultValue:
        """Process one context and return a concrete typed result."""
        ...


@runtime_checkable
class PostprocessProcessor(Protocol):
    """Single-processor compatibility contract used by ``ModelRun``.

    Existing processors continue to receive a concrete ``ModelRunResult`` and
    return a concrete ``PostprocessResult``.  Composition is deliberately not
    implemented here; a future adapter can expose steps through
    :class:`PostprocessStep` while retaining this boundary.
    """

    def process(
        self, model_run: ModelRunResultValue, **kwargs: object
    ) -> PostprocessResultValue:
        """Process a validated model-run result."""
        ...


# Discoverable aliases for users describing the protocol rather than the role.
PostprocessStepProtocol = PostprocessStep
PostprocessorProtocol = PostprocessProcessor
ProcessorProtocol = PostprocessProcessor

__all__ = [
    "ArtifactReconciliation",
    "FailurePolicy",
    "JSONValue",
    "OperationalState",
    "PostprocessContext",
    "PostprocessFailurePolicy",
    "PostprocessProcessor",
    "PostprocessResultValue",
    "PostprocessStep",
    "PostprocessStepProtocol",
    "PostprocessorProtocol",
    "ProcessorProtocol",
    "validate_state_namespace",
]
