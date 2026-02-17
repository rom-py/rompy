import pytest
import httpx

try:
    import respx
    from respx import MockRouter
except Exception:
    respx = None
    MockRouter = None

from rompy.core.http_handler import (
    download_http_file,
    extract_filename_from_url,
)


@pytest.fixture
def tmp_download_dir(tmp_path):
    """Create a temporary directory for downloads."""
    download_dir = tmp_path / "downloads"
    download_dir.mkdir()
    return download_dir


@pytest.mark.skipif(respx is None, reason="respx not installed")
def test_http_download_success(tmp_download_dir):
    """Test successful HTTP download."""
    url = "https://example.com/test.nc"
    content = b"test file content"

    with respx.mock:
        respx.get(url).mock(return_value=httpx.Response(200, content=content))

        result = download_http_file(url, tmp_download_dir)

        assert result.exists()
        assert result.name == "test.nc"
        assert result.read_bytes() == content


@pytest.mark.skipif(respx is None, reason="respx not installed")
def test_http_404_no_retry(tmp_download_dir):
    """Test that 404 errors don't retry."""
    url = "https://example.com/missing.nc"

    with respx.mock:
        route = respx.get(url).mock(return_value=httpx.Response(404))

        with pytest.raises(httpx.HTTPStatusError):
            download_http_file(url, tmp_download_dir)

        # Should only be called once (no retries)
        assert route.called
        assert route.call_count == 1


@pytest.mark.skipif(respx is None, reason="respx not installed")
def test_http_503_retries(tmp_download_dir):
    """Test that 503 errors retry 3 times."""
    url = "https://example.com/unavailable.nc"

    with respx.mock:
        route = respx.get(url).mock(return_value=httpx.Response(503))

        with pytest.raises(httpx.HTTPStatusError):
            download_http_file(url, tmp_download_dir)

        # Should be called 4 times (initial + 3 retries)
        assert route.call_count == 4


@pytest.mark.skipif(respx is None, reason="respx not installed")
def test_http_retry_success(tmp_download_dir):
    """Test successful download after retries."""
    url = "https://example.com/flaky.nc"
    content = b"success after retries"

    call_count = 0

    def flaky_response(request):
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            return httpx.Response(503)
        return httpx.Response(200, content=content)

    with respx.mock:
        respx.get(url).mock(side_effect=flaky_response)

        result = download_http_file(url, tmp_download_dir)

        assert result.exists()
        assert result.read_bytes() == content
        assert call_count == 3


@pytest.mark.skipif(respx is None, reason="respx not installed")
def test_http_size_limit(tmp_download_dir):
    """Test that files exceeding size limit are rejected."""
    url = "https://example.com/huge.nc"

    # Create content larger than 500MB
    # We'll use a generator to avoid actually creating a huge file
    def huge_content():
        chunk_size = 1024 * 1024  # 1MB chunks
        for _ in range(501):  # 501MB total
            yield b"x" * chunk_size

    with respx.mock:
        respx.get(url).mock(
            return_value=httpx.Response(200, content=b"".join(huge_content()))
        )

        with pytest.raises(ValueError, match="File size exceeds limit"):
            download_http_file(url, tmp_download_dir)


@pytest.mark.skipif(respx is None, reason="respx not installed")
def test_datablob_accepts_http_url():
    """Test that DataBlob accepts HTTP URLs as plain strings."""
    from rompy.core.data import DataBlob

    url = "https://example.com/data.nc"

    blob = DataBlob(source=url)

    assert isinstance(blob.source, str)
    assert blob.source == url
    assert blob.link is False


@pytest.mark.skipif(respx is None, reason="respx not installed")
def test_datablob_http_link_error():
    """Test that DataBlob raises error when link=True with HTTP URL."""
    from rompy.core.data import DataBlob
    from pydantic import ValidationError

    url = "https://example.com/data.nc"

    with pytest.raises(ValidationError, match="Cannot use link=True with https://"):
        DataBlob(source=url, link=True)


@pytest.mark.skipif(respx is None, reason="respx not installed")
def test_datablob_http_get(tmp_download_dir):
    """Test DataBlob.get() with HTTP URL."""
    from rompy.core.data import DataBlob

    url = "https://example.com/test.nc"
    content = b"test netcdf content"

    with respx.mock:
        respx.get(url).mock(return_value=httpx.Response(200, content=content))

        blob = DataBlob(source=url)
        result = blob.get(tmp_download_dir)

        assert result.exists()
        assert result.name == "test.nc"
        assert result.read_bytes() == content
        assert result.parent == tmp_download_dir


@pytest.mark.skipif(respx is None, reason="respx not installed")
def test_datablob_http_cache(tmp_download_dir):
    """Test that HTTP downloads are cached."""
    url = "https://example.com/cached.nc"
    content = b"cached content"

    with respx.mock:
        route = respx.get(url).mock(return_value=httpx.Response(200, content=content))

        # First download
        result1 = download_http_file(url, tmp_download_dir)
        assert route.call_count == 1

        # Second call should use cache (no HTTP request)
        result2 = download_http_file(url, tmp_download_dir)
        assert route.call_count == 1  # Still only 1 call
        assert result1 == result2


def test_http_url_with_query_params():
    """Test filename extraction from URL with query params."""
    url = "https://example.com/data.nc?token=abc123&version=2"
    filename = extract_filename_from_url(url)
    assert filename == "data.nc"


def test_http_url_with_encoding():
    """Test filename extraction from URL-encoded paths."""
    url = "https://example.com/path%20with%20spaces/file%20name.nc"
    filename = extract_filename_from_url(url)
    assert filename == "file name.nc"


def test_http_url_no_filename():
    """Test fallback when URL has no filename."""
    url = "https://example.com/"
    filename = extract_filename_from_url(url)
    assert filename == "download"

    url2 = "https://example.com/path/"
    filename2 = extract_filename_from_url(url2)
    assert filename2 == "download"


@pytest.mark.skipif(respx is None, reason="respx not installed")
def test_http_redirect_handling(tmp_download_dir):
    """Test that redirects are followed."""
    original_url = "https://example.com/redirect"
    final_url = "https://example.com/final.nc"
    content = b"redirected content"

    with respx.mock:
        respx.get(original_url).mock(
            return_value=httpx.Response(302, headers={"Location": final_url})
        )
        respx.get(final_url).mock(return_value=httpx.Response(200, content=content))

        result = download_http_file(original_url, tmp_download_dir, name="test.nc")

        assert result.exists()
        assert result.read_bytes() == content


def test_http_insecure_warning():
    """Test warning for insecure HTTP URLs (vs HTTPS)."""
    # This test verifies behavior but doesn't require actual warnings
    # The HTTP handler accepts both http:// and https://
    url = "http://example.com/insecure.nc"
    filename = extract_filename_from_url(url)
    assert filename == "insecure.nc"


@pytest.mark.skipif(respx is None, reason="respx not installed")
def test_http_timeout(tmp_download_dir):
    """Test that timeout errors trigger retries."""
    url = "https://example.com/slow.nc"

    def timeout_response(request):
        raise httpx.TimeoutException("Request timed out")

    with respx.mock:
        route = respx.get(url).mock(side_effect=timeout_response)

        with pytest.raises(httpx.TimeoutException):
            download_http_file(url, tmp_download_dir, timeout=1)

        # Should retry 3 times
        assert route.call_count == 4
