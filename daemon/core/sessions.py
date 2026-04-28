"""Conversation persistence: per-project JSONL transcripts.

Sessions are stored as JSON Lines under
``<config_dir>/projects/<encoded-cwd>/<session-id>.jsonl``. One line per
message — appended as the conversation grows so a crashed REPL still
leaves a complete record on disk. The layout mirrors Claude Code's:
each project (= working directory) gets its own folder, and ``--resume``
lists the recent sessions for the current cwd so the user can pick one.

JSON (not pickle) is used deliberately: session files are treated as
untrusted on read.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from daemon.core import user_config

PROJECTS_DIRNAME = "projects"
SESSION_SUFFIX = ".jsonl"


def projects_dir() -> Path:
    """Return the root directory holding all per-project session folders."""
    return user_config.config_dir() / PROJECTS_DIRNAME


def encode_cwd(cwd: str | os.PathLike[str]) -> str:
    """Encode a working-directory path into a flat folder name.

    Every run of non-alphanumeric characters becomes a single ``-``. The
    encoding is deliberately one-way; the original cwd is preserved inside
    each session file's metadata header.
    """
    return re.sub(r"[^A-Za-z0-9]+", "-", str(cwd)).strip("-") or "root"


def project_dir(cwd: str | os.PathLike[str] | None = None) -> Path:
    """Return the session directory for ``cwd`` (default: current cwd)."""
    return projects_dir() / encode_cwd(cwd if cwd is not None else os.getcwd())


@dataclass(frozen=True)
class SessionMeta:
    """Summary of a stored session, used by the resume picker."""

    session_id: str
    path: Path
    cwd: str
    updated_at: float
    message_count: int
    summary: str


class Session:
    """A live, append-on-write transcript backed by a JSONL file."""

    def __init__(self, path: Path, cwd: str, persisted_count: int = 0) -> None:
        self.path = path
        self.cwd = cwd
        self._persisted = persisted_count

    @property
    def session_id(self) -> str:
        return self.path.stem

    @classmethod
    def new(cls, cwd: str | os.PathLike[str] | None = None) -> Session:
        """Create a new, empty session file in the current project's folder."""
        cwd_str = str(cwd) if cwd is not None else os.getcwd()
        directory = project_dir(cwd_str)
        directory.mkdir(parents=True, exist_ok=True)
        session_id = uuid.uuid4().hex[:16]
        path = directory / f"{session_id}{SESSION_SUFFIX}"
        session = cls(path, cwd_str, persisted_count=0)
        session._write_header()
        return session

    @classmethod
    def open(cls, path: Path) -> tuple[Session, list[dict[str, Any]]]:
        """Open an existing session file, returning the session and its messages."""
        cwd, messages = _read_file(path)
        # _persisted counts only message lines, matching what `sync` will
        # diff against the in-memory `messages` list.
        return cls(path, cwd, persisted_count=len(messages)), messages

    def sync(self, messages: list[dict[str, Any]]) -> None:
        """Append any messages not yet on disk."""
        if self._persisted >= len(messages):
            return
        with self.path.open("a", encoding="utf-8") as f:
            for msg in messages[self._persisted :]:
                f.write(json.dumps({"type": "message", "message": msg}) + "\n")
        self._persisted = len(messages)

    def rewrite(self, messages: list[dict[str, Any]]) -> None:
        """Replace the session contents atomically (used by /rewind)."""
        directory = self.path.parent
        directory.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=directory,
            prefix=".tmp-",
            suffix=SESSION_SUFFIX,
            delete=False,
        ) as tmp:
            tmp.write(_header_line(self.cwd) + "\n")
            for msg in messages:
                tmp.write(json.dumps({"type": "message", "message": msg}) + "\n")
            tmp_path = Path(tmp.name)
        os.replace(tmp_path, self.path)
        self._persisted = len(messages)

    def _write_header(self) -> None:
        with self.path.open("w", encoding="utf-8") as f:
            f.write(_header_line(self.cwd) + "\n")


def list_sessions(cwd: str | os.PathLike[str] | None = None) -> list[SessionMeta]:
    """Return sessions for ``cwd`` (default: current cwd), newest first."""
    directory = project_dir(cwd if cwd is not None else os.getcwd())
    if not directory.is_dir():
        return []
    out: list[SessionMeta] = []
    for path in directory.glob(f"*{SESSION_SUFFIX}"):
        if path.name.startswith("."):
            continue
        meta = _summarize(path)
        if meta is not None:
            out.append(meta)
    out.sort(key=lambda m: m.updated_at, reverse=True)
    return out


def latest_session(cwd: str | os.PathLike[str] | None = None) -> SessionMeta | None:
    """Return the most recently updated session for ``cwd``, if any."""
    sessions = list_sessions(cwd)
    return sessions[0] if sessions else None


def _header_line(cwd: str) -> str:
    return json.dumps(
        {
            "type": "meta",
            "cwd": cwd,
            "created_at": time.time(),
            "schema": 1,
        }
    )


def _read_file(path: Path) -> tuple[str, list[dict[str, Any]]]:
    """Parse a session file. Returns (cwd, messages). Tolerant of corrupt lines."""
    cwd = ""
    messages: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(entry, dict):
                continue
            kind = entry.get("type")
            if kind == "meta":
                cwd = str(entry.get("cwd", cwd))
            elif kind == "message":
                msg = entry.get("message")
                if isinstance(msg, dict):
                    messages.append(msg)
    return cwd, messages


def _summarize(path: Path) -> SessionMeta | None:
    try:
        cwd, messages = _read_file(path)
    except OSError:
        return None
    if not messages:
        return None
    return SessionMeta(
        session_id=path.stem,
        path=path,
        cwd=cwd,
        updated_at=path.stat().st_mtime,
        message_count=len(messages),
        summary=_first_user_preview(messages),
    )


def _first_user_preview(messages: list[dict[str, Any]], limit: int = 80) -> str:
    for msg in messages:
        if msg.get("role") != "user":
            continue
        content = msg.get("content")
        if isinstance(content, str) and content.strip():
            text = content.strip().splitlines()[0]
            return text if len(text) <= limit else text[: limit - 1] + "…"
    return "(no user messages)"


def format_age(updated_at: float, now: float | None = None) -> str:
    """Render a compact relative age like ``5m`` or ``2h``."""
    delta = max(0, int((now if now is not None else time.time()) - updated_at))
    if delta < 60:
        return f"{delta}s"
    if delta < 3600:
        return f"{delta // 60}m"
    if delta < 86400:
        return f"{delta // 3600}h"
    return f"{delta // 86400}d"
