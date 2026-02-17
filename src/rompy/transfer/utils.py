from __future__ import annotations

from urllib.parse import urlparse


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
