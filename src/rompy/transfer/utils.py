from __future__ import annotations

import re
from urllib.parse import unquote, urlparse, urlunparse

_URL_WITH_CREDENTIALS = re.compile(r"\b(?:https?|s3|gs|az|file)://[^\s]+")


def redact_uri(uri: str) -> str:
    """Return a URI identity without userinfo, query credentials, or fragments."""
    parsed = urlparse(str(uri))
    if not parsed.scheme:
        return str(uri).split("#", 1)[0].split("?", 1)[0]
    host = parsed.hostname or ""
    if parsed.port:
        host = f"{host}:{parsed.port}"
    return urlunparse((parsed.scheme.lower(), host, parsed.path, "", "", ""))


def _decoded_forms(value: str) -> set[str]:
    """Return the raw value and its bounded percent-decoded forms."""
    forms = {value}
    current = value
    for _ in range(3):
        decoded = unquote(current)
        if decoded == current:
            break
        forms.add(decoded)
        current = decoded
    return forms


def _sensitive_uri_parts(uri: str) -> set[str]:
    """Collect URI material that must not appear in transfer diagnostics."""
    value = str(uri)
    parsed = urlparse(value)
    parts: set[str] = set()
    for component in (parsed.username, parsed.password, parsed.query, parsed.fragment):
        if component:
            parts.update(_decoded_forms(component))
    if parsed.query:
        for component in parsed.query.split("&"):
            if component:
                parts.update(_decoded_forms(component))
                key, separator, query_value = component.partition("=")
                parts.update(_decoded_forms(key))
                if separator and query_value:
                    parts.update(_decoded_forms(query_value))
    return {part for part in parts if part}


def redact_error(value: object, *uris: str) -> str:
    """Redact URI credentials and their decoded forms from diagnostic text."""
    text = str(value)
    for uri in uris:
        original = str(uri)
        text = text.replace(original, redact_uri(original))
        for part in _sensitive_uri_parts(original):
            text = text.replace(part, "<redacted>")
    return _URL_WITH_CREDENTIALS.sub(
        lambda match: redact_uri(match.group(0)), text
    )


def parse_scheme(uri: str) -> str:
    """
    Return the lower-cased scheme for a URI.
    - Empty scheme or empty input -> 'file'
    - Windows drive letters (e.g., 'C:/path') are treated as file scheme
    - Case-insensitive: returns lowercase
    - For URIs with a real scheme (e.g., 'https', 's3'), return the scheme
    """
    if uri is None:
        return "file"
    parsed = urlparse(uri)
    scheme = (parsed.scheme or "").lower()
    # Treat Windows drive letters like 'C:/path' as file scheme
    if len(scheme) == 1 and scheme.isalpha():
        return "file"
    if scheme == "":
        return "file"
    return scheme


def join_prefix(prefix: str, name: str) -> str:
    """Join a destination prefix with a target filename to create a full URI.

    Handles various URI schemes (file://, s3://, gs://, http://, etc.) and
    plain filesystem paths, ensuring proper path construction without
    double slashes (except in scheme://authority).

    Args:
        prefix: Destination prefix (folder-like). May be a URI with scheme
                (e.g., "s3://bucket/outputs/") or plain path ("/local/outputs/").
        name: Target filename to append to the prefix (e.g., "output.nc").

    Returns:
        Complete destination URI or path.

    Examples:
        >>> join_prefix("s3://bucket/outputs/", "file.nc")
        's3://bucket/outputs/file.nc'

        >>> join_prefix("s3://bucket/outputs", "file.nc")
        's3://bucket/outputs/file.nc'

        >>> join_prefix("/local/outputs/", "file.nc")
        '/local/outputs/file.nc'

        >>> join_prefix("file:///tmp/data/", "file.nc")
        'file:///tmp/data/file.nc'

        >>> join_prefix("gs://bucket", "file.nc")
        'gs://bucket/file.nc'
    """
    parsed = urlparse(prefix)

    if parsed.scheme:
        path = parsed.path
        if not path.endswith("/"):
            path += "/"

        full_path = path + name

        return urlunparse(
            (
                parsed.scheme,
                parsed.netloc,
                full_path,
                parsed.params,
                parsed.query,
                parsed.fragment,
            )
        )
    else:
        prefix_clean = prefix.rstrip("/")
        return f"{prefix_clean}/{name}"
