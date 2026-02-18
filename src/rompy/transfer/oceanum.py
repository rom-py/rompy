"""Oceanum storage transfer implementation using fsspec."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Any, List, Optional

from .base import TransferBase


class OceanumTransfer(TransferBase):
    """Transfer implementation for oceanum:// scheme using fsspec."""

    def __init__(self):
        """Initialize Oceanum transfer with token from environment."""
        self._token = os.environ.get("DATAMESH_TOKEN")
        if not self._token:
            raise ValueError(
                "DATAMESH_TOKEN environment variable not set. "
                "Required for oceanum:// storage access."
            )

        # Lazy import fsspec to avoid hard dependency
        try:
            import fsspec
        except ImportError as e:
            raise ImportError(
                "fsspec is required for oceanum:// storage. "
                "Install with: pip install 'fsspec[oceanum]'"
            ) from e

        # Initialize oceanum filesystem
        self._fs = fsspec.filesystem("oceanum", token=self._token)

    def _strip_scheme(self, uri: str) -> str:
        """Remove oceanum:// scheme prefix if present."""
        if uri.startswith("oceanum://"):
            return uri[len("oceanum://") :]
        return uri

    def get(
        self, uri: str, destdir: Path, name: Optional[str] = None, link: bool = False
    ) -> Path:
        """
        Download from Oceanum storage to local destdir.

        Args:
            uri: oceanum:// URI
            destdir: Local destination directory
            name: Optional name for downloaded file
            link: Ignored for remote storage (always downloads)

        Returns:
            Path to downloaded file
        """
        remote_path = self._strip_scheme(uri)

        # Determine local destination
        if name is None:
            name = Path(remote_path).name

        dest_path = Path(destdir) / name
        Path(destdir).mkdir(parents=True, exist_ok=True)

        # Download using fsspec
        self._fs.get(remote_path, str(dest_path), recursive=False)

        return dest_path

    def exists(self, uri: str) -> bool:
        """Check if path exists in Oceanum storage."""
        remote_path = self._strip_scheme(uri)
        return self._fs.exists(remote_path)

    def list(self, uri: str) -> List[str]:
        """List directory contents in Oceanum storage."""
        remote_path = self._strip_scheme(uri)

        # ls returns full paths, extract just names
        entries = self._fs.ls(remote_path, detail=False)
        return [Path(e).name for e in entries]

    def put(self, local_path: Path, uri: str) -> str:
        """Upload local file to Oceanum storage."""
        remote_path = self._strip_scheme(uri)

        # Upload using fsspec
        self._fs.put(str(local_path), remote_path, recursive=False)

        return f"oceanum://{remote_path}"

    def delete(self, uri: str, recursive: bool = False) -> None:
        """Delete file/directory from Oceanum storage."""
        remote_path = self._strip_scheme(uri)
        self._fs.rm(remote_path, recursive=recursive)

    def stat(self, uri: str) -> Dict[str, Any]:
        """Return file metadata from Oceanum storage."""
        remote_path = self._strip_scheme(uri)

        # fsspec info() returns detailed metadata
        info = self._fs.info(remote_path)

        return {
            "size": info.get("size", 0),
            "type": info.get("type", "unknown"),
            "name": info.get("name", remote_path),
            "mtime": info.get("mtime"),
            **info,  # Include all other metadata
        }
