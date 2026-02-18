"""Cloud storage transfer implementation using cloudpathlib.

Supports S3 (s3://), Google Cloud Storage (gs://), and Azure Blob (az://)
via cloudpathlib's unified interface.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Any, List, Optional

from cloudpathlib import CloudPath, S3Path, GSPath, AzureBlobPath

from .base import TransferBase


class CloudTransfer(TransferBase):
    """
    Transfer implementation for cloud storage via cloudpathlib.

    Supports:
    - S3: s3://bucket/key
    - Google Cloud Storage: gs://bucket/key
    - Azure Blob Storage: az://container/blob

    Credentials are managed via environment variables:
    - S3: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_DEFAULT_REGION
    - GCS: GOOGLE_APPLICATION_CREDENTIALS
    - Azure: AZURE_STORAGE_CONNECTION_STRING
    """

    def _parse_cloud_uri(self, uri: str) -> CloudPath:
        """
        Parse URI string into appropriate CloudPath object.

        Args:
            uri: Cloud storage URI (s3://, gs://, or az://)

        Returns:
            CloudPath object (S3Path, GSPath, or AzureBlobPath)

        Raises:
            ValueError: If URI scheme is not supported
        """
        if uri.startswith("s3://"):
            return S3Path(uri)
        elif uri.startswith("gs://"):
            return GSPath(uri)
        elif uri.startswith("az://"):
            return AzureBlobPath(uri)
        else:
            raise ValueError(
                f"Unsupported cloud URI scheme: {uri}. "
                f"Supported schemes: s3://, gs://, az://"
            )

    def get(
        self, uri: str, destdir: Path, name: Optional[str] = None, link: bool = False
    ) -> Path:
        """
        Download file from cloud storage to local directory.

        Args:
            uri: Cloud storage URI
            destdir: Local destination directory
            name: Optional name for downloaded file (default: use cloud object name)
            link: Ignored for cloud storage (always downloads)

        Returns:
            Path to downloaded file

        Raises:
            FileNotFoundError: If cloud object does not exist
        """
        cloud_path = self._parse_cloud_uri(uri)

        if not cloud_path.exists():
            raise FileNotFoundError(f"Cloud object does not exist: {uri}")

        # Determine destination name
        dest_name = name or cloud_path.name
        dest_path = Path(destdir) / dest_name

        # Ensure destination directory exists
        Path(destdir).mkdir(parents=True, exist_ok=True)

        # Download file
        cloud_path.download_to(dest_path)

        return dest_path

    def exists(self, uri: str) -> bool:
        """Check if cloud object exists."""
        try:
            cloud_path = self._parse_cloud_uri(uri)
            return cloud_path.exists()
        except Exception:
            return False

    def list(self, uri: str) -> List[str]:
        """
        List objects under cloud prefix.

        Args:
            uri: Cloud storage URI (can be directory or file)

        Returns:
            List of object names (not full URIs)

        Raises:
            FileNotFoundError: If cloud prefix does not exist
        """
        cloud_path = self._parse_cloud_uri(uri)

        if not cloud_path.exists():
            raise FileNotFoundError(f"Cloud prefix does not exist: {uri}")

        # If it's a file, return single item
        if cloud_path.is_file():
            return [cloud_path.name]

        # If it's a directory, list contents
        if cloud_path.is_dir():
            return [p.name for p in cloud_path.iterdir()]

        return []

    def put(self, local_path: Path, uri: str) -> str:
        """
        Upload local file to cloud storage.

        Args:
            local_path: Local file path
            uri: Cloud destination URI

        Returns:
            Cloud URI of uploaded object

        Raises:
            FileNotFoundError: If local file does not exist
            ValueError: If local_path is a directory (not supported yet)
        """
        if not local_path.exists():
            raise FileNotFoundError(f"Local file does not exist: {local_path}")

        if not local_path.is_file():
            raise ValueError(
                f"Directory uploads not yet supported: {local_path}. "
                f"Please upload files individually."
            )

        cloud_path = self._parse_cloud_uri(uri)

        # Upload file
        cloud_path.upload_from(local_path)

        return str(cloud_path)

    def delete(self, uri: str, recursive: bool = False) -> None:
        """
        Delete cloud object.

        Args:
            uri: Cloud storage URI
            recursive: If True, delete directory recursively

        Raises:
            ValueError: If trying to delete directory without recursive=True
        """
        cloud_path = self._parse_cloud_uri(uri)

        if not cloud_path.exists():
            return  # Already deleted

        if cloud_path.is_dir():
            if not recursive:
                raise ValueError(
                    f"Cannot delete cloud directory without recursive=True: {uri}"
                )
            # Delete directory recursively
            cloud_path.rmtree()
        else:
            # Delete single file
            cloud_path.unlink()

    def stat(self, uri: str) -> Dict[str, Any]:
        """
        Get metadata for cloud object.

        Args:
            uri: Cloud storage URI

        Returns:
            Dictionary with metadata (size, type, etag, etc.)

        Raises:
            FileNotFoundError: If cloud object does not exist
        """
        cloud_path = self._parse_cloud_uri(uri)

        if not cloud_path.exists():
            raise FileNotFoundError(f"Cloud object does not exist: {uri}")

        stat_result = cloud_path.stat()

        return {
            "size": stat_result.st_size if hasattr(stat_result, "st_size") else None,
            "mtime": stat_result.st_mtime if hasattr(stat_result, "st_mtime") else None,
            "is_file": cloud_path.is_file(),
            "is_dir": cloud_path.is_dir(),
            "type": "file" if cloud_path.is_file() else "directory",
            "uri": str(cloud_path),
            "etag": getattr(stat_result, "etag", None),
        }
