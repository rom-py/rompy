"""Tests for cloud storage transfer backend using cloudpathlib."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from rompy.transfer.cloud import CloudTransfer


@pytest.fixture
def cloud_transfer():
    """Create CloudTransfer instance for testing."""
    return CloudTransfer()


@pytest.fixture
def mock_s3_path():
    """Mock S3Path for testing."""
    with patch("rompy.transfer.cloud.S3Path") as mock:
        yield mock


@pytest.fixture
def mock_gs_path():
    """Mock GSPath for testing."""
    with patch("rompy.transfer.cloud.GSPath") as mock:
        yield mock


@pytest.fixture
def mock_az_path():
    """Mock AzureBlobPath for testing."""
    with patch("rompy.transfer.cloud.AzureBlobPath") as mock:
        yield mock


class TestCloudTransferParsing:
    """Test URI parsing and scheme detection."""

    def test_parse_s3_uri(self, cloud_transfer, mock_s3_path):
        """Test parsing S3 URI."""
        uri = "s3://bucket/key/file.txt"
        result = cloud_transfer._parse_cloud_uri(uri)
        mock_s3_path.assert_called_once_with(uri)

    def test_parse_gs_uri(self, cloud_transfer, mock_gs_path):
        """Test parsing GCS URI."""
        uri = "gs://bucket/key/file.txt"
        result = cloud_transfer._parse_cloud_uri(uri)
        mock_gs_path.assert_called_once_with(uri)

    def test_parse_az_uri(self, cloud_transfer, mock_az_path):
        """Test parsing Azure Blob URI."""
        uri = "az://container/blob/file.txt"
        result = cloud_transfer._parse_cloud_uri(uri)
        mock_az_path.assert_called_once_with(uri)

    def test_parse_unsupported_scheme(self, cloud_transfer):
        """Test error on unsupported scheme."""
        with pytest.raises(ValueError, match="Unsupported cloud URI scheme"):
            cloud_transfer._parse_cloud_uri("ftp://server/file.txt")


class TestCloudTransferGet:
    """Test downloading files from cloud storage."""

    def test_get_s3_file(self, cloud_transfer, mock_s3_path, tmp_path):
        """Test downloading file from S3."""
        # Setup mock
        mock_cloud = MagicMock()
        mock_cloud.exists.return_value = True
        mock_cloud.name = "file.txt"
        mock_cloud.download_to.return_value = None
        mock_s3_path.return_value = mock_cloud

        # Execute
        uri = "s3://bucket/path/file.txt"
        result = cloud_transfer.get(uri, tmp_path)

        # Verify
        assert result == tmp_path / "file.txt"
        mock_cloud.download_to.assert_called_once_with(tmp_path / "file.txt")

    def test_get_with_custom_name(self, cloud_transfer, mock_s3_path, tmp_path):
        """Test downloading with custom destination name."""
        # Setup mock
        mock_cloud = MagicMock()
        mock_cloud.exists.return_value = True
        mock_cloud.name = "original.txt"
        mock_s3_path.return_value = mock_cloud

        # Execute
        result = cloud_transfer.get("s3://bucket/file.txt", tmp_path, name="custom.txt")

        # Verify
        assert result == tmp_path / "custom.txt"
        mock_cloud.download_to.assert_called_once_with(tmp_path / "custom.txt")

    def test_get_nonexistent_file(self, cloud_transfer, mock_s3_path, tmp_path):
        """Test error when downloading nonexistent file."""
        # Setup mock
        mock_cloud = MagicMock()
        mock_cloud.exists.return_value = False
        mock_s3_path.return_value = mock_cloud

        # Execute and verify
        with pytest.raises(FileNotFoundError, match="Cloud object does not exist"):
            cloud_transfer.get("s3://bucket/missing.txt", tmp_path)

    def test_get_link_ignored(self, cloud_transfer, mock_s3_path, tmp_path):
        """Test that link parameter is ignored for cloud storage."""
        # Setup mock
        mock_cloud = MagicMock()
        mock_cloud.exists.return_value = True
        mock_cloud.name = "file.txt"
        mock_s3_path.return_value = mock_cloud

        # Execute with link=True (should be ignored)
        result = cloud_transfer.get("s3://bucket/file.txt", tmp_path, link=True)

        # Verify download was called (not symlink)
        mock_cloud.download_to.assert_called_once()


class TestCloudTransferExists:
    """Test checking existence of cloud objects."""

    def test_exists_true(self, cloud_transfer, mock_s3_path):
        """Test exists returns True for existing object."""
        mock_cloud = MagicMock()
        mock_cloud.exists.return_value = True
        mock_s3_path.return_value = mock_cloud

        assert cloud_transfer.exists("s3://bucket/file.txt") is True

    def test_exists_false(self, cloud_transfer, mock_s3_path):
        """Test exists returns False for nonexistent object."""
        mock_cloud = MagicMock()
        mock_cloud.exists.return_value = False
        mock_s3_path.return_value = mock_cloud

        assert cloud_transfer.exists("s3://bucket/missing.txt") is False

    def test_exists_handles_exceptions(self, cloud_transfer, mock_s3_path):
        """Test exists returns False on exceptions."""
        mock_s3_path.side_effect = Exception("Connection error")

        assert cloud_transfer.exists("s3://bucket/file.txt") is False


class TestCloudTransferList:
    """Test listing cloud objects."""

    def test_list_file(self, cloud_transfer, mock_s3_path):
        """Test listing single file."""
        mock_cloud = MagicMock()
        mock_cloud.exists.return_value = True
        mock_cloud.is_file.return_value = True
        mock_cloud.is_dir.return_value = False
        mock_cloud.name = "file.txt"
        mock_s3_path.return_value = mock_cloud

        result = cloud_transfer.list("s3://bucket/file.txt")
        assert result == ["file.txt"]

    def test_list_directory(self, cloud_transfer, mock_s3_path):
        """Test listing directory contents."""
        # Setup mock directory
        mock_file1 = MagicMock()
        mock_file1.name = "file1.txt"
        mock_file2 = MagicMock()
        mock_file2.name = "file2.txt"

        mock_cloud = MagicMock()
        mock_cloud.exists.return_value = True
        mock_cloud.is_file.return_value = False
        mock_cloud.is_dir.return_value = True
        mock_cloud.iterdir.return_value = [mock_file1, mock_file2]
        mock_s3_path.return_value = mock_cloud

        result = cloud_transfer.list("s3://bucket/prefix/")
        assert result == ["file1.txt", "file2.txt"]

    def test_list_nonexistent(self, cloud_transfer, mock_s3_path):
        """Test error listing nonexistent prefix."""
        mock_cloud = MagicMock()
        mock_cloud.exists.return_value = False
        mock_s3_path.return_value = mock_cloud

        with pytest.raises(FileNotFoundError, match="Cloud prefix does not exist"):
            cloud_transfer.list("s3://bucket/missing/")


class TestCloudTransferPut:
    """Test uploading files to cloud storage."""

    def test_put_file(self, cloud_transfer, mock_s3_path, tmp_path):
        """Test uploading local file to cloud."""
        # Create local file
        local_file = tmp_path / "test.txt"
        local_file.write_text("content")

        # Setup mock
        mock_cloud = MagicMock()
        mock_cloud.__str__.return_value = "s3://bucket/dest.txt"
        mock_s3_path.return_value = mock_cloud

        # Execute
        result = cloud_transfer.put(local_file, "s3://bucket/dest.txt")

        # Verify
        assert result == "s3://bucket/dest.txt"
        mock_cloud.upload_from.assert_called_once_with(local_file)

    def test_put_nonexistent_file(self, cloud_transfer, mock_s3_path, tmp_path):
        """Test error uploading nonexistent file."""
        with pytest.raises(FileNotFoundError, match="Local file does not exist"):
            cloud_transfer.put(tmp_path / "missing.txt", "s3://bucket/dest.txt")

    def test_put_directory_not_supported(self, cloud_transfer, mock_s3_path, tmp_path):
        """Test error uploading directory."""
        with pytest.raises(ValueError, match="Directory uploads not yet supported"):
            cloud_transfer.put(tmp_path, "s3://bucket/dest/")


class TestCloudTransferDelete:
    """Test deleting cloud objects."""

    def test_delete_file(self, cloud_transfer, mock_s3_path):
        """Test deleting single file."""
        mock_cloud = MagicMock()
        mock_cloud.exists.return_value = True
        mock_cloud.is_dir.return_value = False
        mock_s3_path.return_value = mock_cloud

        cloud_transfer.delete("s3://bucket/file.txt")
        mock_cloud.unlink.assert_called_once()

    def test_delete_nonexistent_ignored(self, cloud_transfer, mock_s3_path):
        """Test deleting nonexistent object (no-op)."""
        mock_cloud = MagicMock()
        mock_cloud.exists.return_value = False
        mock_s3_path.return_value = mock_cloud

        cloud_transfer.delete("s3://bucket/missing.txt")
        mock_cloud.unlink.assert_not_called()

    def test_delete_directory_recursive(self, cloud_transfer, mock_s3_path):
        """Test deleting directory recursively."""
        mock_cloud = MagicMock()
        mock_cloud.exists.return_value = True
        mock_cloud.is_dir.return_value = True
        mock_s3_path.return_value = mock_cloud

        cloud_transfer.delete("s3://bucket/prefix/", recursive=True)
        mock_cloud.rmtree.assert_called_once()

    def test_delete_directory_without_recursive(self, cloud_transfer, mock_s3_path):
        """Test error deleting directory without recursive flag."""
        mock_cloud = MagicMock()
        mock_cloud.exists.return_value = True
        mock_cloud.is_dir.return_value = True
        mock_s3_path.return_value = mock_cloud

        with pytest.raises(
            ValueError, match="Cannot delete cloud directory without recursive=True"
        ):
            cloud_transfer.delete("s3://bucket/prefix/", recursive=False)


class TestCloudTransferStat:
    """Test getting cloud object metadata."""

    def test_stat_file(self, cloud_transfer, mock_s3_path):
        """Test getting file metadata."""
        # Setup mock
        mock_stat = MagicMock()
        mock_stat.st_size = 1024
        mock_stat.st_mtime = 1234567890.0
        mock_stat.etag = "abc123"

        mock_cloud = MagicMock()
        mock_cloud.exists.return_value = True
        mock_cloud.stat.return_value = mock_stat
        mock_cloud.is_file.return_value = True
        mock_cloud.is_dir.return_value = False
        mock_cloud.__str__.return_value = "s3://bucket/file.txt"
        mock_s3_path.return_value = mock_cloud

        # Execute
        result = cloud_transfer.stat("s3://bucket/file.txt")

        # Verify
        assert result["size"] == 1024
        assert result["mtime"] == 1234567890.0
        assert result["is_file"] is True
        assert result["is_dir"] is False
        assert result["type"] == "file"
        assert result["uri"] == "s3://bucket/file.txt"
        assert result["etag"] == "abc123"

    def test_stat_nonexistent(self, cloud_transfer, mock_s3_path):
        """Test error getting metadata for nonexistent object."""
        mock_cloud = MagicMock()
        mock_cloud.exists.return_value = False
        mock_s3_path.return_value = mock_cloud

        with pytest.raises(FileNotFoundError, match="Cloud object does not exist"):
            cloud_transfer.stat("s3://bucket/missing.txt")
