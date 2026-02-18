from __future__ import annotations

from urllib.parse import urlparse, urlunparse


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
