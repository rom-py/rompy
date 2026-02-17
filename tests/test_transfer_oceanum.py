"""Tests for OceanumTransfer implementation."""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from rompy.transfer.oceanum import OceanumTransfer


@pytest.fixture
def mock_fs():
    """Mock fsspec filesystem."""
    fs = MagicMock()
    fs.exists.return_value = True
    fs.ls.return_value = ["file1.nc", "file2.nc"]
    fs.info.return_value = {"size": 1024, "type": "file"}
    return fs


@pytest.fixture
def transfer_with_token(monkeypatch, mock_fs):
    """Create OceanumTransfer with DATAMESH_TOKEN set and mocked fsspec."""
    monkeypatch.setenv("DATAMESH_TOKEN", "test-token-123")
    with patch("fsspec.filesystem", return_value=mock_fs):
        transfer = OceanumTransfer()
        transfer._fs = mock_fs  # Replace with mock after creation
        return transfer


def test_oceanum_missing_token():
    """Test OceanumTransfer raises error without DATAMESH_TOKEN."""
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ValueError, match="DATAMESH_TOKEN"):
            OceanumTransfer()


def test_oceanum_get(transfer_with_token, mock_fs, tmp_path):
    """Test OceanumTransfer.get() calls fs.get()."""
    uri = "oceanum://bucket/path/file.nc"
    result = transfer_with_token.get(uri, tmp_path, link=False)

    mock_fs.get.assert_called_once()
    assert result == tmp_path / "file.nc"


def test_oceanum_get_with_name(transfer_with_token, mock_fs, tmp_path):
    """Test OceanumTransfer.get() with custom filename."""
    uri = "oceanum://bucket/path/file.nc"
    result = transfer_with_token.get(uri, tmp_path, name="custom.nc", link=False)

    mock_fs.get.assert_called_once()
    assert result == tmp_path / "custom.nc"


def test_oceanum_exists(transfer_with_token, mock_fs):
    """Test OceanumTransfer.exists() calls fs.exists()."""
    uri = "oceanum://bucket/path/file.nc"
    result = transfer_with_token.exists(uri)

    mock_fs.exists.assert_called_once_with("bucket/path/file.nc")
    assert result is True


def test_oceanum_list(transfer_with_token, mock_fs):
    """Test OceanumTransfer.list() calls fs.ls()."""
    uri = "oceanum://bucket/path/"
    result = transfer_with_token.list(uri)

    mock_fs.ls.assert_called_once_with("bucket/path/", detail=False)
    assert result == ["file1.nc", "file2.nc"]


def test_oceanum_put(transfer_with_token, mock_fs, tmp_path):
    """Test OceanumTransfer.put() calls fs.put()."""
    test_file = tmp_path / "test.nc"
    test_file.write_text("data")

    uri = "oceanum://bucket/path/test.nc"
    result = transfer_with_token.put(test_file, uri)

    mock_fs.put.assert_called_once_with(
        str(test_file), "bucket/path/test.nc", recursive=False
    )
    assert result == uri


def test_oceanum_delete(transfer_with_token, mock_fs):
    """Test OceanumTransfer.delete() calls fs.rm()."""
    uri = "oceanum://bucket/path/file.nc"
    transfer_with_token.delete(uri, recursive=False)

    mock_fs.rm.assert_called_once_with("bucket/path/file.nc", recursive=False)


def test_oceanum_delete_recursive(transfer_with_token, mock_fs):
    """Test OceanumTransfer.delete() with recursive=True."""
    uri = "oceanum://bucket/path/dir/"
    transfer_with_token.delete(uri, recursive=True)

    mock_fs.rm.assert_called_once_with("bucket/path/dir/", recursive=True)


def test_oceanum_stat(transfer_with_token, mock_fs):
    """Test OceanumTransfer.stat() calls fs.info()."""
    uri = "oceanum://bucket/path/file.nc"
    result = transfer_with_token.stat(uri)

    mock_fs.info.assert_called_once_with("bucket/path/file.nc")
    # Check that result contains expected fields (implementation adds mtime, name, and spreads **info)
    assert result["size"] == 1024
    assert result["type"] == "file"
    assert "mtime" in result
    assert "name" in result
