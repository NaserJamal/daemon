"""Pre-image stack for `/undo`.

`write` and `edit` mutate files. Before each mutation we snapshot the
current bytes (or note "didn't exist") and push the snapshot onto a
process-wide stack. `/undo` pops the top entry and restores it — either
overwriting the file with the saved bytes or deleting it if it didn't
exist before.

The stack is in-memory and cleared by `/clear`. Persisting checkpoints
across REPL restarts is intentionally out of scope for now.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Checkpoint:
    """A single pre-image entry."""

    path: str
    content: bytes | None
    tool: str


_stack: list[Checkpoint] = []


def snapshot(path: str) -> tuple[bytes | None, bool]:
    """Read the current bytes of ``path``. Returns ``(content, existed)``.

    ``existed`` is False if the file isn't present; ``content`` is then
    None. Permission errors on a present file propagate so the caller
    can choose to skip the checkpoint.
    """
    try:
        with open(path, "rb") as f:
            return f.read(), True
    except FileNotFoundError:
        return None, False


def push(path: str, tool: str, content: bytes | None) -> None:
    """Record a captured pre-image. Called after the tool succeeds."""
    _stack.append(Checkpoint(path=path, content=content, tool=tool))


def undo() -> Checkpoint | None:
    """Pop the latest checkpoint and restore the file. Returns it, or None.

    Restoring a checkpoint whose ``content`` is None means the file
    didn't exist before the tool ran — so we delete it. A missing file
    on delete is treated as success (nothing to undo).
    """
    if not _stack:
        return None
    cp = _stack.pop()
    if cp.content is None:
        try:
            os.unlink(cp.path)
        except FileNotFoundError:
            pass
        return cp
    with open(cp.path, "wb") as f:
        f.write(cp.content)
    return cp


def clear() -> None:
    """Drop every pending checkpoint."""
    _stack.clear()


def count() -> int:
    """How many checkpoints are currently on the stack."""
    return len(_stack)
