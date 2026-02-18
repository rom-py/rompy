"""Tests for TransferManager."""

import pytest
from pathlib import Path

from rompy.transfer.manager import (
    TransferManager,
    TransferFailurePolicy,
    TransferItemResult,
    TransferBatchResult,
)


@pytest.fixture
def temp_files(tmp_path):
    """Create temporary test files."""
    file1 = tmp_path / "file1.txt"
    file2 = tmp_path / "file2.txt"
    file1.write_text("content1")
    file2.write_text("content2")
    return [file1, file2]


@pytest.fixture
def temp_dest(tmp_path):
    """Create temporary destination directories."""
    dest1 = tmp_path / "dest1"
    dest2 = tmp_path / "dest2"
    dest1.mkdir()
    dest2.mkdir()
    return [str(dest1), str(dest2)]


def test_transfer_manager_single_file_single_dest(temp_files, temp_dest):
    """Test transferring a single file to a single destination."""
    manager = TransferManager()
    files = [temp_files[0]]
    destinations = [temp_dest[0]]
    name_map = {temp_files[0]: "renamed.txt"}

    result = manager.transfer_files(files, destinations, name_map)

    assert result.total == 1
    assert result.succeeded == 1
    assert result.failed == 0
    assert result.all_succeeded()
    assert len(result.items) == 1

    item = result.items[0]
    assert item.local_path == temp_files[0]
    assert item.dest_prefix == temp_dest[0]
    assert item.target_name == "renamed.txt"
    assert item.ok is True
    assert item.error is None

    transferred = Path(item.dest_uri)
    assert transferred.exists()
    assert transferred.read_text() == "content1"


def test_transfer_manager_multiple_files_multiple_dest(temp_files, temp_dest):
    """Test transferring multiple files to multiple destinations."""
    manager = TransferManager()
    name_map = {temp_files[0]: "file1_renamed.txt", temp_files[1]: "file2_renamed.txt"}

    result = manager.transfer_files(temp_files, temp_dest, name_map)

    assert result.total == 4
    assert result.succeeded == 4
    assert result.failed == 0
    assert result.all_succeeded()
    assert len(result.items) == 4

    for dest in temp_dest:
        assert (Path(dest) / "file1_renamed.txt").exists()
        assert (Path(dest) / "file2_renamed.txt").exists()
        assert (Path(dest) / "file1_renamed.txt").read_text() == "content1"
        assert (Path(dest) / "file2_renamed.txt").read_text() == "content2"


def test_transfer_manager_continue_on_failure(temp_files, tmp_path):
    """Test CONTINUE policy records failures but continues."""
    manager = TransferManager()
    good_dest = str(tmp_path / "good")
    bad_dest = "/nonexistent/readonly/path"
    Path(good_dest).mkdir()

    destinations = [good_dest, bad_dest]
    name_map = {temp_files[0]: "file.txt"}

    result = manager.transfer_files(
        [temp_files[0]], destinations, name_map, policy=TransferFailurePolicy.CONTINUE
    )

    assert result.total == 2
    assert result.succeeded == 1
    assert result.failed == 1
    assert not result.all_succeeded()

    assert result.items[0].ok is True
    assert result.items[1].ok is False
    assert result.items[1].error is not None


def test_transfer_manager_fail_fast_on_error(temp_files, tmp_path):
    """Test FAIL_FAST policy raises on first failure."""
    manager = TransferManager()
    good_dest = str(tmp_path / "good")
    bad_dest = "/nonexistent/readonly/path"
    Path(good_dest).mkdir()

    destinations = [bad_dest, good_dest]
    name_map = {temp_files[0]: "file.txt"}

    with pytest.raises(Exception):
        manager.transfer_files(
            [temp_files[0]],
            destinations,
            name_map,
            policy=TransferFailurePolicy.FAIL_FAST,
        )


def test_transfer_batch_result_all_succeeded():
    """Test TransferBatchResult.all_succeeded() helper."""
    result_success = TransferBatchResult(total=2, succeeded=2, failed=0, items=[])
    assert result_success.all_succeeded()

    result_failure = TransferBatchResult(total=2, succeeded=1, failed=1, items=[])
    assert not result_failure.all_succeeded()


def test_transfer_manager_empty_lists(tmp_path):
    """Test transfer with empty file list."""
    manager = TransferManager()
    result = manager.transfer_files([], [str(tmp_path)], {})

    assert result.total == 0
    assert result.succeeded == 0
    assert result.failed == 0
    assert result.all_succeeded()
    assert len(result.items) == 0
