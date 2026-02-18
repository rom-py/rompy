"""File transfer implementation for local filesystem operations."""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse

from .base import TransferBase


class FileTransfer(TransferBase):
    """Transfer implementation for local file:// scheme and plain file paths."""

    def _parse_file_uri(self, uri: str) -> Path:
        """Convert file:// URI or plain path to Path object."""
        if uri.startswith("file://"):
            # Remove file:// prefix and convert to path
            parsed = urlparse(uri)
            return Path(parsed.path)
        return Path(uri)

    def get(
        self, uri: str, destdir: Path, name: Optional[str] = None, link: bool = False
    ) -> Path:
        """
        Retrieve local file/directory and place it in destdir.

        Args:
            uri: File URI or path string
            destdir: Destination directory
            name: Optional name for the destination (default: use source name)
            link: If True, create symlink instead of copy (local only)

        Returns:
            Path to the retrieved file/directory in destdir
        """
        source = self._parse_file_uri(uri)

        if not source.exists():
            raise FileNotFoundError(f"Source path does not exist: {source}")

        # Determine destination name
        dest_name = name or source.name
        dest_path = Path(destdir) / dest_name

        # Ensure destination directory exists
        Path(destdir).mkdir(parents=True, exist_ok=True)

        if link:
            # Create symlink (relative path from destdir to source)
            if dest_path.exists() or dest_path.is_symlink():
                dest_path.unlink()

            # Create relative symlink if possible
            try:
                rel_source = os.path.relpath(source, destdir)
                os.symlink(rel_source, dest_path)
            except (ValueError, OSError):
                # Fall back to absolute path if relative fails
                os.symlink(source.absolute(), dest_path)
        else:
            # Copy file or directory
            if source.is_file():
                dest_path.write_bytes(source.read_bytes())
            elif source.is_dir():
                if dest_path.exists():
                    shutil.rmtree(dest_path)
                shutil.copytree(source, dest_path)
            else:
                raise ValueError(f"Source is neither file nor directory: {source}")

        return dest_path

    def exists(self, uri: str) -> bool:
        """Check if local path exists."""
        path = self._parse_file_uri(uri)
        return path.exists()

    def list(self, uri: str) -> List[str]:
        """List directory contents, or return single item for file."""
        path = self._parse_file_uri(uri)

        if not path.exists():
            raise FileNotFoundError(f"Path does not exist: {path}")

        if path.is_file():
            return [path.name]

        return [p.name for p in path.iterdir()]

    def put(self, local_path: Path, uri: str) -> str:
        """Copy local file to destination path."""
        dest = self._parse_file_uri(uri)

        # Ensure destination parent directory exists
        dest.parent.mkdir(parents=True, exist_ok=True)

        if local_path.is_file():
            shutil.copy2(local_path, dest)
        elif local_path.is_dir():
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(local_path, dest)
        else:
            raise ValueError(f"Local path is neither file nor directory: {local_path}")

        return str(dest)

    def delete(self, uri: str, recursive: bool = False) -> None:
        """Delete file or directory."""
        path = self._parse_file_uri(uri)

        if not path.exists():
            return  # Already deleted

        if path.is_file() or path.is_symlink():
            path.unlink()
        elif path.is_dir():
            if recursive:
                shutil.rmtree(path)
            else:
                path.rmdir()  # Fails if directory not empty

    def stat(self, uri: str) -> Dict[str, Any]:
        """Return file metadata."""
        path = self._parse_file_uri(uri)

        if not path.exists():
            raise FileNotFoundError(f"Path does not exist: {path}")

        stat_result = path.stat()

        return {
            "size": stat_result.st_size,
            "mtime": stat_result.st_mtime,
            "ctime": stat_result.st_ctime,
            "is_file": path.is_file(),
            "is_dir": path.is_dir(),
            "is_symlink": path.is_symlink(),
            "type": (
                "file"
                if path.is_file()
                else ("directory" if path.is_dir() else "symlink")
            ),
            "path": str(path.absolute()),
        }
