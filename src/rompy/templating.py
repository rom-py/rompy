"""
Template variable substitution for YAML configurations.

This module provides ${VAR} style variable substitution for rompy config files,
supporting environment variables, defaults, and datetime processing filters.

Examples:
    Basic substitution:
        filename: "/path/to/wind_input_${CYCLE}.nc"

    With defaults:
        output_dir: "${OUTPUT_ROOT:-./output}/runs"

    Datetime filters:
        run_id: "cycle_${CYCLE|strftime:%Y%m%d}"
        prev_cycle: "${CYCLE|as_datetime|shift:-1d}"
"""

import os
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional, Union

from rompy.logging import get_logger

logger = get_logger(__name__)

# Regex pattern for ${VAR}, ${VAR:-default}, ${VAR|filter:arg|filter2}
# Captures: variable name, default value (optional), filter chain (optional)
TEMPLATE_PATTERN = re.compile(
    r"\$\{([A-Za-z_][A-Za-z0-9_]*)"  # Variable name (group 1)
    r"(?::-((?:[^|}]|\\[|}])*?))?"  # Optional default :- (group 2)
    r"(?:\|([^}]+))?"  # Optional filter chain | (group 3)
    r"\}"
)


class TemplateError(Exception):
    """Raised when template rendering fails."""

    pass


class TemplateContext:
    """Context for template variable resolution.

    Wraps a dict (typically os.environ) and provides variable lookup with
    type conversion and default handling.
    """

    def __init__(self, context: Optional[Dict[str, Any]] = None):
        """Initialize template context.

        Args:
            context: Dict of variables (defaults to os.environ)
        """
        self.context = context if context is not None else dict(os.environ)

    def get(self, name: str, default: Optional[str] = None) -> Any:
        """Get variable value with optional default.

        Args:
            name: Variable name
            default: Default value if variable not found

        Returns:
            Variable value (typed if possible)

        Raises:
            TemplateError: If variable not found and no default
        """
        if name in self.context:
            return self.context[name]

        if default is not None:
            return default

        raise TemplateError(
            f"Variable '${{{name}}}' not found in context and no default provided"
        )

    def set(self, name: str, value: Any):
        """Set variable in context (for nested resolution)."""
        self.context[name] = value


def parse_datetime(value: Any, fmt: Optional[str] = None) -> datetime:
    """Parse datetime from string.

    Args:
        value: String or datetime object
        fmt: strptime format (if None, tries ISO-8601)

    Returns:
        datetime object

    Raises:
        TemplateError: If parsing fails
    """
    if isinstance(value, datetime):
        return value

    if not isinstance(value, str):
        raise TemplateError(
            f"Cannot parse datetime from {type(value).__name__}: {value}"
        )

    # Try ISO-8601 first
    if fmt is None:
        try:
            # Handle various ISO formats
            for iso_fmt in [
                "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%dT%H:%M:%S.%f",
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d",
            ]:
                try:
                    return datetime.strptime(value, iso_fmt)
                except ValueError:
                    continue
            # Try fromisoformat as fallback
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except (ValueError, AttributeError) as e:
            raise TemplateError(f"Cannot parse ISO datetime from '{value}': {e}")
    else:
        # Use provided format
        try:
            return datetime.strptime(value, fmt)
        except ValueError as e:
            raise TemplateError(
                f"Cannot parse datetime from '{value}' with format '{fmt}': {e}"
            )


def shift_datetime(dt: datetime, delta_str: str) -> datetime:
    """Shift datetime by delta string.

    Args:
        dt: datetime object
        delta_str: Delta string like "+1d", "-6h", "+30m"

    Returns:
        Shifted datetime

    Raises:
        TemplateError: If delta format invalid
    """
    match = re.match(r"^([+-]?)(\d+)([dhms])$", delta_str)
    if not match:
        raise TemplateError(
            f"Invalid shift format '{delta_str}'. Expected format: [+|-]<number><d|h|m|s> "
            f"(e.g., '+1d', '-6h', '+30m')"
        )

    sign, amount, unit = match.groups()
    amount = int(amount)
    if sign == "-":
        amount = -amount

    if unit == "d":
        delta = timedelta(days=amount)
    elif unit == "h":
        delta = timedelta(hours=amount)
    elif unit == "m":
        delta = timedelta(minutes=amount)
    elif unit == "s":
        delta = timedelta(seconds=amount)
    else:
        raise TemplateError(f"Unknown time unit '{unit}' (expected d, h, m, s)")

    return dt + delta


def apply_filter(value: Any, filter_spec: str) -> Any:
    """Apply a single filter to a value.

    Args:
        value: Input value
        filter_spec: Filter specification (e.g., "strftime:%Y%m%d", "shift:-1d")

    Returns:
        Filtered value

    Raises:
        TemplateError: If filter unknown or fails
    """
    # Parse filter name and argument
    if ":" in filter_spec:
        filter_name, filter_arg = filter_spec.split(":", 1)
    else:
        filter_name = filter_spec
        filter_arg = None

    filter_name = filter_name.strip()

    # Apply filter
    if filter_name == "as_datetime":
        # Parse datetime with optional format
        return parse_datetime(value, filter_arg)

    elif filter_name == "strftime":
        # Format datetime
        if not filter_arg:
            raise TemplateError(
                f"Filter 'strftime' requires format argument (e.g., strftime:%Y%m%d)"
            )

        # Ensure value is datetime
        if not isinstance(value, datetime):
            value = parse_datetime(value)

        return value.strftime(filter_arg)

    elif filter_name == "shift":
        # Shift datetime by delta
        if not filter_arg:
            raise TemplateError(
                f"Filter 'shift' requires delta argument (e.g., shift:-1d)"
            )

        # Ensure value is datetime
        if not isinstance(value, datetime):
            value = parse_datetime(value)

        return shift_datetime(value, filter_arg)

    else:
        raise TemplateError(
            f"Unknown filter '{filter_name}'. Available filters: as_datetime, strftime, shift"
        )


def apply_filters(value: Any, filter_chain: str) -> Any:
    """Apply a chain of filters to a value.

    Args:
        value: Input value
        filter_chain: Pipe-separated filters (e.g., "as_datetime|shift:-1d|strftime:%Y%m%d")

    Returns:
        Filtered value
    """
    filters = filter_chain.split("|")
    for filter_spec in filters:
        filter_spec = filter_spec.strip()
        if filter_spec:
            value = apply_filter(value, filter_spec)

    return value


def render_string(template: str, context: TemplateContext, strict: bool = True) -> Any:
    """Render a single template string.

    Args:
        template: Template string (may contain multiple ${...} expressions)
        context: Template context
        strict: Raise error on unresolved variables

    Returns:
        Rendered value (preserves type if template is exactly one expression)
    """
    # Check if template is exactly one expression (for type preservation)
    exact_match = TEMPLATE_PATTERN.fullmatch(template)

    if exact_match:
        # Single expression - preserve type
        var_name, default, filter_chain = exact_match.groups()

        # Get variable value
        try:
            value = context.get(var_name, default)
        except TemplateError:
            if strict:
                raise
            return template  # Keep unresolved

        # Apply filters if present
        if filter_chain:
            try:
                value = apply_filters(value, filter_chain)
            except TemplateError as e:
                if strict:
                    raise TemplateError(
                        f"Filter error in '${{{var_name}|{filter_chain}}}': {e}"
                    )
                return template  # Keep unresolved

        # Type conversion for string values (mimics bash-like behavior)
        if isinstance(value, str):
            # Try bool conversion
            if value.lower() in ("true", "yes", "1"):
                return True
            elif value.lower() in ("false", "no", "0"):
                return False

            # Try int conversion
            try:
                return int(value)
            except ValueError:
                pass

            # Try float conversion
            try:
                return float(value)
            except ValueError:
                pass

        return value

    else:
        # Multiple expressions or embedded - always stringify
        def replace_match(match):
            var_name = match.group(1)
            default = match.group(2)
            filter_chain = match.group(3)

            # Get variable value
            try:
                value = context.get(var_name, default)
            except TemplateError:
                if strict:
                    raise
                return match.group(0)  # Keep original ${...}

            # Apply filters if present
            if filter_chain:
                try:
                    value = apply_filters(value, filter_chain)
                except TemplateError as e:
                    if strict:
                        raise TemplateError(
                            f"Filter error in '${{{var_name}|{filter_chain}}}': {e}"
                        )
                    return match.group(0)  # Keep original ${...}

            # Always stringify in embedded context
            return str(value)

        return TEMPLATE_PATTERN.sub(replace_match, template)


def render_templates(
    data: Any,
    context: Optional[Dict[str, Any]] = None,
    strict: bool = True,
) -> Any:
    """Recursively render templates in data structure.

    Walks dict/list/str recursively and replaces ${VAR} expressions.

    Args:
        data: Data structure (dict, list, str, or primitive)
        context: Variable context (defaults to os.environ)
        strict: Raise error on unresolved variables

    Returns:
        Rendered data structure

    Examples:
        >>> render_templates({"path": "/data/${USER}/file"})
        {"path": "/data/john/file"}

        >>> render_templates({"cycle": "${CYCLE|as_datetime|shift:-1d}"})
        {"cycle": datetime(2023, 1, 1)}
    """
    ctx = TemplateContext(context)
    return _render_recursive(data, ctx, strict)


def _render_recursive(data: Any, context: TemplateContext, strict: bool) -> Any:
    """Recursively render templates (internal)."""

    if isinstance(data, dict):
        # Render dict recursively
        result = {}
        for key, value in data.items():
            # Render key if it contains templates (rare but possible)
            if isinstance(key, str) and "${" in key:
                try:
                    key = render_string(key, context, strict)
                except TemplateError as e:
                    logger.warning(f"Failed to render dict key '{key}': {e}")

            # Render value
            result[key] = _render_recursive(value, context, strict)

        return result

    elif isinstance(data, list):
        # Render list recursively
        return [_render_recursive(item, context, strict) for item in data]

    elif isinstance(data, str):
        # Render string if it contains templates
        if "${" in data:
            return render_string(data, context, strict)
        return data

    else:
        # Primitives (int, float, bool, None) pass through
        return data
