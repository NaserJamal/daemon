"""Tests for the fetch tool."""

from __future__ import annotations

import urllib.error
from email.message import Message
from typing import Any
from unittest.mock import patch

from daemon.tools import run_tool
from daemon.tools.fetch import _html_to_text


class _FakeHeaders:
    def __init__(self, content_type: str) -> None:
        self._headers = {"Content-Type": content_type}

    def get(self, key: str, default: str = "") -> str:
        return self._headers.get(key, default)


class _FakeResponse:
    """Minimal stand-in for urlopen()'s context-managed response."""

    def __init__(self, body: bytes, content_type: str = "text/plain; charset=utf-8") -> None:
        self._body = body
        self.headers = _FakeHeaders(content_type)

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, *_: Any) -> None:
        return None

    def read(self, n: int = -1) -> bytes:
        if n < 0 or n >= len(self._body):
            return self._body
        return self._body[:n]


def _urlopen_returning(response: _FakeResponse) -> Any:
    return patch("daemon.tools.fetch.urllib.request.urlopen", return_value=response)


class TestFetchTool:
    def test_plain_text(self) -> None:
        with _urlopen_returning(_FakeResponse(b"hello world")):
            result = run_tool("fetch", {"url": "https://example.test/"})
        assert result == "hello world"

    def test_html_is_stripped(self) -> None:
        html = b"<html><body><h1>Hi</h1><p>Para</p><script>alert(1)</script></body></html>"
        with _urlopen_returning(_FakeResponse(html, content_type="text/html; charset=utf-8")):
            result = run_tool("fetch", {"url": "https://example.test/"})
        assert "Hi" in result
        assert "Para" in result
        assert "alert(1)" not in result

    def test_truncation(self) -> None:
        body = b"x" * 100
        with _urlopen_returning(_FakeResponse(body)):
            result = run_tool("fetch", {"url": "https://example.test/", "max_bytes": 10})
        assert result.startswith("xxxxxxxxxx")
        assert "truncated at 10 bytes" in result

    def test_rejects_non_http_scheme(self) -> None:
        result = run_tool("fetch", {"url": "file:///etc/passwd"})
        assert result.startswith("error: unsupported scheme")

    def test_rejects_missing_host(self) -> None:
        result = run_tool("fetch", {"url": "http:///nopath"})
        assert result == "error: invalid url"

    def test_http_error_returns_string(self) -> None:
        err = urllib.error.HTTPError(
            "https://example.test/", 404, "Not Found", hdrs=Message(), fp=None
        )
        with patch("daemon.tools.fetch.urllib.request.urlopen", side_effect=err):
            result = run_tool("fetch", {"url": "https://example.test/"})
        assert result == "error: HTTP 404 Not Found"

    def test_url_error_returns_string(self) -> None:
        err = urllib.error.URLError("name resolution failed")
        with patch("daemon.tools.fetch.urllib.request.urlopen", side_effect=err):
            result = run_tool("fetch", {"url": "https://nope.invalid/"})
        assert "name resolution failed" in result

    def test_timeout_returns_string(self) -> None:
        with patch(
            "daemon.tools.fetch.urllib.request.urlopen", side_effect=TimeoutError("timed out")
        ):
            result = run_tool("fetch", {"url": "https://slow.test/"})
        assert "timed out" in result

    def test_charset_decoded(self) -> None:
        body = "héllo".encode("latin-1")
        with _urlopen_returning(_FakeResponse(body, content_type="text/plain; charset=latin-1")):
            result = run_tool("fetch", {"url": "https://example.test/"})
        assert result == "héllo"

    def test_unknown_charset_falls_back_to_utf8(self) -> None:
        with _urlopen_returning(_FakeResponse(b"hi", content_type="text/plain; charset=bogus-1")):
            result = run_tool("fetch", {"url": "https://example.test/"})
        assert result == "hi"

    def test_user_denied(self) -> None:
        from daemon.core import config

        original = config._settings
        config._settings = config.Settings(yolo=False)
        try:
            with patch("daemon.safety.confirm.input", return_value="n"):
                result = run_tool("fetch", {"url": "https://example.test/"})
        finally:
            config._settings = original
        assert result == "error: user denied execution"

    def test_registered_in_schema(self) -> None:
        from daemon.tools import get_schema

        names = [item["function"]["name"] for item in get_schema()]
        assert "fetch" in names


class TestHtmlExtractor:
    def test_collapses_whitespace(self) -> None:
        out = _html_to_text("<p>a    b</p>\n<p>c</p>")
        assert "a b" in out
        assert "c" in out

    def test_drops_style_block(self) -> None:
        out = _html_to_text("<style>body{color:red}</style><p>visible</p>")
        assert out == "visible"

    def test_handles_nested_skip_tags(self) -> None:
        out = _html_to_text("<head><title>t</title></head><body><p>shown</p></body>")
        assert "t" not in out
        assert "shown" in out
