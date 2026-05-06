"""Debug logging for API requests and responses.

When enabled (via ``--debug``, ``DAEMON_DEBUG=1``, or ``DAEMON_DEBUG=<path>``),
every chat-completion request body and assembled response is appended as a
JSON line to a log file. Streaming responses are logged as the final
assembled payload, which matches what the rest of daemon sees.

The log is JSONL: each line is ``{"ts", "kind", "data"}``. ``kind`` is
``request``, ``response``, ``http_error``, or ``enabled``.
"""

from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_FILENAME = "daemon-debug.log"
TRUTHY = ("1", "true", "yes", "on")

_lock = threading.Lock()
_path: Path | None = None


def enable(path: str | os.PathLike[str] | None = None) -> Path:
    """Turn debug logging on. Defaults to ``daemon-debug.log`` in the cwd."""
    global _path
    p = Path(path) if path else Path.cwd() / DEFAULT_FILENAME
    p.parent.mkdir(parents=True, exist_ok=True)
    _path = p
    log_event("enabled", {"path": str(p)})
    return p


def disable() -> None:
    """Turn debug logging off (mainly for tests)."""
    global _path
    _path = None


def is_enabled() -> bool:
    return _path is not None


def current_path() -> Path | None:
    return _path


def log_event(kind: str, data: Any) -> None:
    """Append a single JSON line to the debug log. No-op if disabled."""
    if _path is None:
        return
    record = {
        "ts": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
        "kind": kind,
        "data": data,
    }
    line = json.dumps(record, default=str, ensure_ascii=False)
    with _lock:
        try:
            with _path.open("a", encoding="utf-8") as f:
                f.write(line + "\n")
        except OSError:
            # Logging errors must never crash the REPL.
            pass


def from_env() -> Path | None:
    """Honor ``DAEMON_DEBUG``. Truthy strings enable to the default path; any
    other non-empty value is treated as the log path. Returns the path or
    None if the env var is unset or empty.
    """
    raw = os.environ.get("DAEMON_DEBUG", "").strip()
    if not raw:
        return None
    if raw.lower() in TRUTHY:
        return enable()
    return enable(raw)
