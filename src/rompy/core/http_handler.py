"""HTTP download handler with retry logic and atomic writes.

This module provides utilities for downloading files from HTTP/HTTPS URLs with:
- Retry logic with exponential backoff for transient failures
- Atomic writes (download to temp file, then rename)
- Caching support (skip download if file already exists)
- File size limits to prevent excessive downloads

Main Functions
--------------
download_http_file : Download a file from HTTP/HTTPS URL
retry_with_backoff : Decorator for retry logic
extract_filename_from_url : Extract filename from URL path

Constants
---------
MAX_RETRIES : Maximum retry attempts (default: 3)
RETRY_DELAY_BASE : Base delay for exponential backoff (default: 1 second)
HTTP_TIMEOUT : Default timeout in seconds (default: 30)
MAX_FILE_SIZE : Maximum file size in bytes (default: 500MB)

"""

import functools
import logging
import os
import tempfile
import time
from pathlib import Path
from typing import Optional
from urllib.parse import unquote, urlparse

import httpx

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_DELAY_BASE = 1  # seconds
HTTP_TIMEOUT = 30
MAX_FILE_SIZE = 500 * 1024 * 1024  # 500MB


def retry_with_backoff(max_retries=MAX_RETRIES, base_delay=RETRY_DELAY_BASE):
    """Decorator for retry logic with exponential backoff.

    Retries on:
    - 5xx status codes
    - Timeout errors
    - Connection errors

    Does NOT retry on:
    - 4xx status codes (client errors)
    - ValueError (e.g., file size limit)

    Parameters
    ----------
    max_retries : int
        Maximum number of retry attempts (default: 3)
    base_delay : float
        Base delay in seconds for exponential backoff (default: 1)

    Returns
    -------
    callable
        Decorated function with retry logic
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except httpx.HTTPStatusError as e:
                    if 400 <= e.response.status_code < 500:
                        logger.error(
                            f"Client error {e.response.status_code}, not retrying"
                        )
                        raise

                    if 500 <= e.response.status_code < 600:
                        last_exception = e
                        if attempt < max_retries:
                            delay = base_delay * (2**attempt)
                            logger.warning(
                                f"Server error {e.response.status_code}, "
                                f"retrying in {delay}s (attempt {attempt + 1}/{max_retries})"
                            )
                            time.sleep(delay)
                            continue
                        else:
                            logger.error(
                                f"Max retries reached after {max_retries} attempts"
                            )
                            raise

                    raise

                except (
                    httpx.TimeoutException,
                    httpx.ConnectError,
                    httpx.RemoteProtocolError,
                ) as e:
                    last_exception = e
                    if attempt < max_retries:
                        delay = base_delay * (2**attempt)
                        logger.warning(
                            f"Network error ({type(e).__name__}), "
                            f"retrying in {delay}s (attempt {attempt + 1}/{max_retries})"
                        )
                        time.sleep(delay)
                        continue
                    else:
                        logger.error(
                            f"Max retries reached after {max_retries} attempts"
                        )
                        raise

            if last_exception:
                raise last_exception

        return wrapper

    return decorator


def extract_filename_from_url(url: str) -> str:
    """Extract filename from URL, handling query params and encoding.

    Parameters
    ----------
    url : str
        URL to extract filename from

    Returns
    -------
    str
        Extracted and decoded filename

    Examples
    --------
    >>> extract_filename_from_url("https://example.com/data.nc")
    'data.nc'
    >>> extract_filename_from_url("https://example.com/data.nc?token=abc")
    'data.nc'
    >>> extract_filename_from_url("https://example.com/path%20with%20spaces/file.nc")
    'file.nc'
    >>> extract_filename_from_url("https://example.com/")
    'download'
    """
    parsed = urlparse(url)
    path = parsed.path

    # Check if path ends with "/" (indicates directory, not a file)
    if path.endswith("/"):
        return "download"

    # Remove query params (already handled by urlparse)
    # Get the last component of the path
    filename = path.rstrip("/").split("/")[-1] if path.rstrip("/") else ""

    # Decode URL encoding
    if filename:
        filename = unquote(filename)

    # Fallback if no filename in path
    if not filename or filename == "":
        filename = "download"

    return filename


@retry_with_backoff()
def _download_with_retry(url: str, temp_path: Path, timeout: int) -> int:
    """Internal function to download with retry logic.

    Parameters
    ----------
    url : str
        URL to download from
    temp_path : Path
        Path to write downloaded content to
    timeout : int
        Timeout in seconds

    Returns
    -------
    int
        Size of downloaded file in bytes
    """
    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        with client.stream("GET", url) as response:
            response.raise_for_status()

            total_size = 0
            with open(temp_path, "wb") as f:
                for chunk in response.iter_bytes(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        total_size += len(chunk)

                        # Check size limit
                        if total_size > MAX_FILE_SIZE:
                            raise ValueError(
                                f"File size exceeds limit of {MAX_FILE_SIZE / (1024 * 1024):.1f}MB"
                            )

            return total_size


def download_http_file(
    url: str, dest_dir: Path, name: Optional[str] = None, timeout: int = HTTP_TIMEOUT
) -> Path:
    """Download file from HTTP URL with caching and atomic writes.

    Features:
    - Caching: Skip download if file exists and size > 0
    - Atomic writes: Download to temp file, then rename
    - Retry logic: Exponential backoff on transient failures
    - Size limit: 500MB maximum file size

    Parameters
    ----------
    url : str
        HTTP/HTTPS URL to download from
    dest_dir : Path
        Destination directory for downloaded file
    name : str, optional
        Override filename (default: extract from URL)
    timeout : int, optional
        Timeout in seconds (default: 30)

    Returns
    -------
    Path
        Path to downloaded file

    Raises
    ------
    httpx.HTTPStatusError
        On HTTP errors (4xx, 5xx after retries)
    ValueError
        On file size limit exceeded
    """
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)

    # Determine filename
    if name is None:
        name = extract_filename_from_url(url)

    dest_path = dest_dir / name

    # Check cache (if file exists and size > 0, return it)
    if dest_path.exists() and dest_path.stat().st_size > 0:
        logger.info(f"File already exists, using cache: {dest_path}")
        return dest_path

    logger.info(f"Downloading {url} to {dest_path}")

    # Create temp file in same directory for atomic rename
    temp_fd, temp_path_str = tempfile.mkstemp(
        dir=dest_dir, prefix=".tmp_", suffix=f"_{name}"
    )
    temp_path = Path(temp_path_str)

    try:
        # Close the file descriptor, we'll open it for writing in the download function
        os.close(temp_fd)

        # Download to temp file with retry logic
        file_size = _download_with_retry(url, temp_path, timeout)

        logger.info(f"Downloaded {file_size / (1024 * 1024):.2f}MB")

        # Atomic rename to final location
        temp_path.rename(dest_path)

        return dest_path

    except Exception:
        if temp_path.exists():
            temp_path.unlink()
        raise
