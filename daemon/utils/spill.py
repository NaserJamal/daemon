"""Spill oversized tool output to a temp file instead of into the context.

Tools whose output has no natural bound pass it through `spill()`. Output
that comfortably fits comes back unchanged; anything larger is written to a
file under `<tempdir>/daemon-output/` and replaced by a head+tail preview
naming that path, which the model can then read, grep, or script against.
"""

from __future__ import annotations

import re
import tempfile
from pathlib import Path

MAX_INLINE_CHARS = 50_000
MAX_INLINE_LINES = 2_000
HEAD_LINES = 50
TAIL_LINES = 20
PREVIEW_CHARS = 2_000


def spill(text: str, label: str) -> str:
    """Return `text` inline, or a preview of it plus the path holding the whole thing.

    `label` names the producing tool (e.g. "bash") and prefixes the temp file.
    """
    lines = text.splitlines()
    if len(text) <= MAX_INLINE_CHARS and len(lines) <= MAX_INLINE_LINES:
        return text

    try:
        location = f"full output: {_write(text, label)} - read or grep that path"
    except OSError as err:
        location = f"full output could not be saved: {err}"

    head = "\n".join(lines[:HEAD_LINES])[:PREVIEW_CHARS]
    tail = "\n".join(lines[-TAIL_LINES:])[-PREVIEW_CHARS:]
    omitted = len(lines) - HEAD_LINES - TAIL_LINES
    middle = f"[... {omitted} lines omitted ...]" if omitted > 0 else "[... output omitted ...]"
    header = (
        f"[{label}: {len(lines)} lines, {len(text)} chars; showing the first "
        f"{HEAD_LINES} and last {TAIL_LINES}. {location}]"
    )
    return f"{header}\n\n{head}\n\n{middle}\n\n{tail}"


def _write(text: str, label: str) -> Path:
    """Write `text` to a uniquely named temp file and return its path."""
    directory = Path(tempfile.gettempdir()) / "daemon-output"
    directory.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^A-Za-z0-9.-]+", "-", label).strip("-")[:40] or "output"
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        prefix=f"{slug}-",
        suffix=".txt",
        dir=directory,
        delete=False,
    ) as handle:
        handle.write(text)
        return Path(handle.name)
