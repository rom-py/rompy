"""Small conformance helpers for independently installed step plugins.

Plugin projects can call :func:`assert_step_conforms` from their own tests;
this module does not import a plugin or permit a plugin to own a sidecar.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import TypeAdapter

from rompy.core.responses import PostprocessResult
from .protocol import PostprocessContext, PostprocessStep


def assert_step_conforms(step: object, context: PostprocessContext) -> Any:
    """Execute and validate a plugin step at the public protocol boundary."""
    if not isinstance(step, PostprocessStep):
        raise TypeError("plugin must provide a name and process(context) method")
    if not isinstance(context, PostprocessContext):
        raise TypeError("plugin context must be PostprocessContext")
    result = step.process(context)
    return TypeAdapter(PostprocessResult).validate_python(result)


def assert_no_sidecar_ownership(step: object, workspace: Path) -> None:
    """Detect the canonical sidecar being written by a plugin test."""
    sidecar = Path(workspace) / "postprocess_result.json"
    if sidecar.exists():
        raise AssertionError(
            "postprocess steps must not create postprocess_result.json; the core runner owns it"
        )


__all__ = ["assert_no_sidecar_ownership", "assert_step_conforms"]
