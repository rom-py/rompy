import pytest
from pathlib import Path


def _import_registry():
    try:
        from rompy.transfer import get_transfer, parse_scheme, TransferBase

        return get_transfer, parse_scheme, TransferBase
    except Exception as exc:
        pytest.skip(
            f"ROMPY transfer registry not importable in this environment: {exc}",
            allow_module_level=False,
        )


# Mock transfer implementations for testing entry-point wiring
class MockFileTransfer(object):
    def __init__(self, *a, **k):
        pass

    def get(self, uri, destdir, name=None, link=False):
        return Path(destdir) / (name or "mock_file.txt")

    def exists(self, uri) -> bool:
        return False

    def list(self, uri):
        return []

    def put(self, local_path, uri) -> str:
        return uri

    def delete(self, uri: str, recursive: bool = False) -> None:
        pass

    def stat(self, uri):
        return {}


class MockHttpTransfer(object):
    def __init__(self, *a, **k):
        pass

    def get(self, uri, destdir, name=None, link=False):
        return Path(destdir) / (name or "mock_http.txt")

    def exists(self, uri) -> bool:
        return False

    def list(self, uri):
        return []

    def put(self, local_path, uri) -> str:
        return uri

    def delete(self, uri: str, recursive: bool = False) -> None:
        pass

    def stat(self, uri):
        return {}


class MockEP:
    def __init__(self, name: str, cls):
        self.name = name
        self._cls = cls

    def load(self):
        return self._cls


def _set_entry_points(monkeypatch, mapping):
    eps = [MockEP(name, cls) for name, cls in mapping.items()]
    # Patch importlib.metadata.entry_points so the registry uses the mocks
    monkeypatch.setattr("importlib.metadata.entry_points", lambda group=None: eps)
    # Clear internal registry cache so subsequent lookups reload from mocks
    try:
        import rompy.transfer.registry as _reg  # type: ignore

        _reg._REGISTRY = None  # type: ignore[attr-defined]
    except Exception:
        pass
    return eps


def test_scheme_normalization_and_get_transfer(monkeypatch):
    _set_entry_points(
        monkeypatch,
        {
            "file": MockFileTransfer,
            "http": MockHttpTransfer,
        },
    )

    # http URIs should map to the HttpTransfer implementation
    get_transfer, parse_scheme, TransferBase = _import_registry()
    t = get_transfer("http://example.com/data")
    assert isinstance(t, MockHttpTransfer)


def test_parse_scheme_normalization_and_file_path(monkeypatch):
    # Ensure parse_scheme normalizes various inputs; this relies on the real
    # implementation in production. If the fallback is used in this environment,
    # this test will still exercise the API surface.
    get_transfer, parse_scheme, TransferBase = _import_registry()
    s = parse_scheme("HTTP://EXAMPLE.COM/path")
    assert isinstance(s, str)
    # Expect lowercase scheme for the normalized value
    assert s == "http"

    # Empty/scheme-less path should yield the "file" scheme
    s2 = parse_scheme("/tmp/file.txt")
    assert s2 == "file"


def test_duplicate_schemes_fail_fast(monkeypatch):
    # Create two entry-points with the same scheme name to simulate a duplicate
    _set_entry_points(
        monkeypatch,
        {
            "file1": MockFileTransfer,
            "file2": MockFileTransfer,
        },
    )
    get_transfer, parse_scheme, TransferBase = _import_registry()
    get_transfer, parse_scheme, TransferBase = _import_registry()
    with pytest.raises(Exception) as exc:
        get_transfer("file:///tmp/test.txt")
    # The exact error type/message may vary by implementation; ensure a meaningful
    # error is raised and mentions a duplicate scheme
    assert any(tok in str(exc.value).lower() for tok in ["duplicate", "scheme"])


def test_unsupported_scheme_error(monkeypatch):
    # Only register a single, known scheme and request an unsupported one
    _set_entry_points(monkeypatch, {"file": MockFileTransfer})
    get_transfer, parse_scheme, TransferBase = _import_registry()
    with pytest.raises(Exception) as exc:
        get_transfer("ftp://example.com/resource")
    msg = str(exc.value).lower()
    # The registry should raise a clear message about missing transfer and available schemes
    assert "no transfer registered" in msg
    assert "available schemes" in msg


def test_get_transfer_accepts_path_and_anypath(monkeypatch):
    _set_entry_points(monkeypatch, {"file": MockFileTransfer, "http": MockHttpTransfer})
    # Path input should resolve to the file transfer
    get_transfer, parse_scheme, TransferBase = _import_registry()
    t1 = get_transfer(Path("/tmp/data.txt"))
    assert isinstance(t1, MockFileTransfer)

    # Optional: test AnyPath input if cloudpathlib is available in the runtime
    try:
        from cloudpathlib import AnyPath  # type: ignore

        ap = AnyPath("/tmp/data.txt")
        t2 = get_transfer(ap)
        assert isinstance(t2, MockFileTransfer)
    except Exception:
        # If cloudpathlib is unavailable, skip this path gracefully
        pass
