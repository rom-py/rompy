"""HTTP/HTTPS transfer implementation (read-only)."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Any, List, Optional

from .base import TransferBase
from .exceptions import UnsupportedOperation


class HttpTransfer(TransferBase):
    """Transfer implementation for http:// and https:// schemes (read-only)."""

    def get(
        self, uri: str, destdir: Path, name: Optional[str] = None, link: bool = False
    ) -> Path:
        """
        Download HTTP/HTTPS resource using existing http_handler.

        Args:
            uri: HTTP/HTTPS URL
            destdir: Destination directory
            name: Optional name for downloaded file
            link: Ignored for HTTP (always downloads)

        Returns:
            Path to downloaded file
        """
        # Import here to avoid circular dependency
        from rompy.core.http_handler import download_http_file

        # Use existing HTTP download handler
        return download_http_file(url=uri, dest_dir=destdir, name=name)

    def exists(self, uri: str) -> bool:
        """Not supported for HTTP - would require HEAD request."""
        raise UnsupportedOperation("http", "exists")

    def list(self, uri: str) -> List[str]:
        """Not supported for HTTP - no directory listing."""
        raise UnsupportedOperation("http", "list")

    def put(self, local_path: Path, uri: str) -> str:
        """Not supported for HTTP - read-only."""
        raise UnsupportedOperation("http", "put")

    def delete(self, uri: str, recursive: bool = False) -> None:
        """Not supported for HTTP - read-only."""
        raise UnsupportedOperation("http", "delete")

    def stat(self, uri: str) -> Dict[str, Any]:
        """Not supported for HTTP - would require HEAD request."""
        raise UnsupportedOperation("http", "stat")
