"""Tests for FileTransfer implementation."""

import os
from pathlib import Path

import pytest

from rompy.transfer.file import FileTransfer
from rompy.transfer.exceptions import UnsupportedOperation


@pytest.fixture
def transfer():
    return FileTransfer()


@pytest.fixture
def temp_source_file(tmp_path):
    source = tmp_path / "source.txt"
    source.write_text("test content")
    return source


@pytest.fixture
def temp_source_dir(tmp_path):
    source_dir = tmp_path / "source_dir"
    source_dir.mkdir()
    (source_dir / "file1.txt").write_text("content1")
    (source_dir / "file2.txt").write_text("content2")
    return source_dir


def test_file_copy(transfer, temp_source_file, tmp_path):
    """Test FileTransfer.get() copies file."""
    destdir = tmp_path / "dest"
    destdir.mkdir()

    result = transfer.get(str(temp_source_file), destdir, link=False)

    assert result.exists()
    assert result.read_text() == "test content"
    assert result != temp_source_file
    assert not result.is_symlink()


def test_file_copy_with_name(transfer, temp_source_file, tmp_path):
    """Test FileTransfer.get() copies file with custom name."""
    destdir = tmp_path / "dest"
    destdir.mkdir()

    result = transfer.get(str(temp_source_file), destdir, name="custom.txt", link=False)

    assert result.name == "custom.txt"
    assert result.read_text() == "test content"


def test_file_link(transfer, temp_source_file, tmp_path):
    """Test FileTransfer.get() creates symlink."""
    destdir = tmp_path / "dest"
    destdir.mkdir()

    result = transfer.get(str(temp_source_file), destdir, link=True)

    assert result.exists()
    assert result.is_symlink()
    assert result.read_text() == "test content"
    assert result.resolve() == temp_source_file.resolve()


def test_file_link_relative_path(transfer, temp_source_file, tmp_path):
    """Test FileTransfer.get() creates relative symlink."""
    destdir = tmp_path / "dest"
    destdir.mkdir()

    result = transfer.get(str(temp_source_file), destdir, link=True)

    link_target = os.readlink(result)
    assert not Path(link_target).is_absolute()


def test_file_exists(transfer, temp_source_file):
    """Test FileTransfer.exists() for existing file."""
    assert transfer.exists(str(temp_source_file)) is True


def test_file_not_exists(transfer, tmp_path):
    """Test FileTransfer.exists() for non-existing file."""
    assert transfer.exists(str(tmp_path / "missing.txt")) is False


def test_file_list_directory(transfer, temp_source_dir):
    """Test FileTransfer.list() lists directory contents."""
    items = transfer.list(str(temp_source_dir))

    assert len(items) == 2
    assert "file1.txt" in items
    assert "file2.txt" in items


def test_file_list_file(transfer, temp_source_file):
    """Test FileTransfer.list() returns single item for file."""
    items = transfer.list(str(temp_source_file))

    assert items == [temp_source_file.name]


def test_file_put(transfer, temp_source_file, tmp_path):
    """Test FileTransfer.put() copies file to destination."""
    dest_uri = str(tmp_path / "dest" / "output.txt")

    result_uri = transfer.put(temp_source_file, dest_uri)

    assert result_uri == dest_uri
    result_path = Path(dest_uri)
    assert result_path.exists()
    assert result_path.read_text() == "test content"


def test_file_delete(transfer, temp_source_file):
    """Test FileTransfer.delete() removes file."""
    assert temp_source_file.exists()

    transfer.delete(str(temp_source_file), recursive=False)

    assert not temp_source_file.exists()


def test_file_delete_directory_recursive(transfer, temp_source_dir):
    """Test FileTransfer.delete() removes directory recursively."""
    assert temp_source_dir.exists()
    assert (temp_source_dir / "file1.txt").exists()

    transfer.delete(str(temp_source_dir), recursive=True)

    assert not temp_source_dir.exists()


def test_file_stat(transfer, temp_source_file):
    """Test FileTransfer.stat() returns file metadata."""
    stat_dict = transfer.stat(str(temp_source_file))

    assert "size" in stat_dict
    assert "mtime" in stat_dict
    assert stat_dict["size"] == len("test content")
    assert stat_dict["type"] == "file"
