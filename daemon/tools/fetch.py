"""Fetch tool: HTTP GET that returns the response body as text."""

from __future__ import annotations

import re
import urllib.error
import urllib.request
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urlparse

from daemon.tools.base import BaseTool
from daemon.tools.registry import register_tool
from daemon.utils.spill import spill

DEFAULT_MAX_BYTES = 1_000_000
TIMEOUT_SECONDS = 30
USER_AGENT = "daemon-fetch/1.0"


@register_tool
class FetchTool(BaseTool):
    name = "fetch"
    description = (
        "HTTP GET a URL and return the response body as text. HTML is reduced to "
        "readable text. A large body is written to a temp file and only a preview "
        "comes back. Truncates at max_bytes (default 1_000_000). Only http/https "
        "URLs are accepted."
    )
    parameters = {"url": "string", "max_bytes": "integer?"}

    def execute(self, args: dict[str, Any]) -> str:
        url = args["url"]
        max_bytes = max(1, args.get("max_bytes", DEFAULT_MAX_BYTES))

        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return f"error: unsupported scheme {parsed.scheme!r} (only http/https)"
        if not parsed.netloc:
            return "error: invalid url"

        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
                content_type = response.headers.get("Content-Type", "")
                raw = response.read(max_bytes + 1)
        except urllib.error.HTTPError as err:
            return f"error: HTTP {err.code} {err.reason}"
        except urllib.error.URLError as err:
            return f"error: {err.reason}"
        except (TimeoutError, OSError) as err:
            return f"error: {err}"

        truncated = len(raw) > max_bytes
        if truncated:
            raw = raw[:max_bytes]

        encoding = _charset(content_type) or "utf-8"
        text: str
        try:
            text = raw.decode(encoding, errors="replace")
        except LookupError:
            text = raw.decode("utf-8", errors="replace")

        if "html" in content_type.lower():
            text = _html_to_text(text)

        if truncated:
            text = text.rstrip() + f"\n(truncated at {max_bytes} bytes)"
        return spill(text, f"fetch {parsed.netloc}")


_CHARSET_RE = re.compile(r"charset=([^\s;]+)", re.IGNORECASE)


def _charset(content_type: str) -> str | None:
    match = _CHARSET_RE.search(content_type)
    return match.group(1).strip("'\"") if match else None


class _TextExtractor(HTMLParser):
    """Strip tags, drop script/style, and emit a roughly readable text block."""

    # Void elements are excluded: they have no end tag, so skipping on them would
    # never unwind. They carry no text anyway.
    SKIP_TAGS = frozenset({"script", "style", "noscript", "head", "title"})
    BREAK_TAGS = frozenset({"p", "br", "div", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6"})

    def __init__(self) -> None:
        super().__init__()
        self._buf: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, _attrs: list[tuple[str, str | None]]) -> None:
        if tag in self.SKIP_TAGS:
            self._skip_depth += 1
        elif tag in self.BREAK_TAGS:
            self._buf.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in self.SKIP_TAGS and self._skip_depth > 0:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._skip_depth == 0:
            self._buf.append(data)

    def text(self) -> str:
        joined = "".join(self._buf)
        joined = re.sub(r"[ \t]+", " ", joined)
        joined = re.sub(r" *\n *", "\n", joined)
        joined = re.sub(r"\n{3,}", "\n\n", joined)
        return joined.strip()


def _html_to_text(html: str) -> str:
    parser = _TextExtractor()
    parser.feed(html)
    parser.close()
    return parser.text()
