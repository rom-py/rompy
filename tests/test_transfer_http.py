"""Tests for HttpTransfer implementation."""

from pathlib import Path

import httpx
import pytest

try:
    import respx
except ImportError:
    respx = None

from rompy.transfer.http import HttpTransfer
from rompy.transfer.exceptions import UnsupportedOperation


@pytest.fixture
def transfer():
    return HttpTransfer()


@pytest.mark.skipif(respx is None, reason="respx not installed")
def test_http_get(transfer, tmp_path):
    """Test HttpTransfer.get() downloads file via http_handler."""
    url = "https://example.com/test.nc"
    content = b"test netcdf content"

    with respx.mock:
        respx.get(url).mock(return_value=httpx.Response(200, content=content))

        result = transfer.get(url, tmp_path, link=False)

        assert result.exists()
        assert result.read_bytes() == content
        assert result.name == "test.nc"


@pytest.mark.skipif(respx is None, reason="respx not installed")
def test_http_get_with_name(transfer, tmp_path):
    """Test HttpTransfer.get() with custom filename."""
    url = "https://example.com/test.nc"
    content = b"test netcdf content"

    with respx.mock:
        respx.get(url).mock(return_value=httpx.Response(200, content=content))

        result = transfer.get(url, tmp_path, name="custom.nc", link=False)

        assert result.exists()
        assert result.name == "custom.nc"
        assert result.read_bytes() == content


@pytest.mark.skipif(respx is None, reason="respx not installed")
def test_http_get_ignores_link(transfer, tmp_path):
    """Test HttpTransfer.get() ignores link=True (always downloads)."""
    url = "https://example.com/test.nc"
    content = b"test netcdf content"

    with respx.mock:
        respx.get(url).mock(return_value=httpx.Response(200, content=content))

        result = transfer.get(url, tmp_path, link=True)

        assert result.exists()
        assert not result.is_symlink()
        assert result.read_bytes() == content


def test_http_exists_unsupported(transfer):
    """Test HttpTransfer.exists() raises UnsupportedOperation."""
    with pytest.raises(UnsupportedOperation, match="exists.*http"):
        transfer.exists("https://example.com/test.nc")


def test_http_list_unsupported(transfer):
    """Test HttpTransfer.list() raises UnsupportedOperation."""
    with pytest.raises(UnsupportedOperation, match="list.*http"):
        transfer.list("https://example.com/")


def test_http_put_unsupported(transfer, tmp_path):
    """Test HttpTransfer.put() raises UnsupportedOperation."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("content")

    with pytest.raises(UnsupportedOperation, match="put.*http"):
        transfer.put(test_file, "https://example.com/test.txt")


def test_http_delete_unsupported(transfer):
    """Test HttpTransfer.delete() raises UnsupportedOperation."""
    with pytest.raises(UnsupportedOperation, match="delete.*http"):
        transfer.delete("https://example.com/test.nc")


def test_http_stat_unsupported(transfer):
    """Test HttpTransfer.stat() raises UnsupportedOperation."""
    with pytest.raises(UnsupportedOperation, match="stat.*http"):
        transfer.stat("https://example.com/test.nc")
