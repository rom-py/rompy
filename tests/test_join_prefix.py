"""Tests for join_prefix utility."""

import pytest

from rompy.transfer.utils import join_prefix


def test_join_prefix_s3_with_trailing_slash():
    """Test joining S3 prefix with trailing slash."""
    result = join_prefix("s3://bucket/outputs/", "file.nc")
    assert result == "s3://bucket/outputs/file.nc"


def test_join_prefix_s3_without_trailing_slash():
    """Test joining S3 prefix without trailing slash."""
    result = join_prefix("s3://bucket/outputs", "file.nc")
    assert result == "s3://bucket/outputs/file.nc"


def test_join_prefix_local_path_with_trailing_slash():
    """Test joining local path with trailing slash."""
    result = join_prefix("/local/outputs/", "file.nc")
    assert result == "/local/outputs/file.nc"


def test_join_prefix_local_path_without_trailing_slash():
    """Test joining local path without trailing slash."""
    result = join_prefix("/local/outputs", "file.nc")
    assert result == "/local/outputs/file.nc"


def test_join_prefix_file_uri():
    """Test joining file:// URI."""
    result = join_prefix("file:///tmp/data/", "file.nc")
    assert result == "file:///tmp/data/file.nc"


def test_join_prefix_gs_bucket():
    """Test joining Google Cloud Storage bucket."""
    result = join_prefix("gs://bucket", "file.nc")
    assert result == "gs://bucket/file.nc"


def test_join_prefix_nested_path():
    """Test joining with nested prefix."""
    result = join_prefix("s3://bucket/path/to/outputs/", "file.nc")
    assert result == "s3://bucket/path/to/outputs/file.nc"


def test_join_prefix_relative_path():
    """Test joining relative path."""
    result = join_prefix("outputs/data", "file.nc")
    assert result == "outputs/data/file.nc"
