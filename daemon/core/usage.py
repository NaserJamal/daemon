"""Running token-usage tracker for the REPL.

A single process-wide :class:`Usage` accumulator is kept in module state so
slash commands and the turn loop can read and update it without threading a
context object through every call site. Reset it via :func:`reset` (the
``/clear`` command does this), feed each API response into :func:`add_response`,
and read totals via :func:`current` or :func:`format_summary`.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any


@dataclass(frozen=True)
class Usage:
    """Cumulative token counts for the current session."""

    input_tokens: int = 0
    output_tokens: int = 0
    requests: int = 0

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


_usage = Usage()
_show_per_turn = False


def current() -> Usage:
    """Return the current cumulative usage."""
    return _usage


def reset() -> None:
    """Zero the usage counters. Per-turn display preference is preserved."""
    global _usage
    _usage = Usage()


def set_show_per_turn(enabled: bool) -> None:
    """Control whether the REPL prints a usage line after each turn."""
    global _show_per_turn
    _show_per_turn = enabled


def show_per_turn() -> bool:
    """Whether the REPL is currently printing per-turn usage."""
    return _show_per_turn


def add_response(payload: dict[str, Any]) -> None:
    """Accumulate the ``usage`` block from a chat-completion response.

    Missing or malformed usage blocks are silently ignored — a server that
    omits usage shouldn't break the REPL.
    """
    global _usage
    raw = payload.get("usage")
    if not isinstance(raw, dict):
        return
    _usage = replace(
        _usage,
        input_tokens=_usage.input_tokens + _coerce_int(raw.get("prompt_tokens")),
        output_tokens=_usage.output_tokens + _coerce_int(raw.get("completion_tokens")),
        requests=_usage.requests + 1,
    )


def format_summary() -> str:
    """Compact one-line summary of the current totals."""
    u = _usage
    if u.requests == 0:
        return "no usage recorded yet"
    return (
        f"{u.requests} request{'s' if u.requests != 1 else ''} | "
        f"in: {u.input_tokens:,} | out: {u.output_tokens:,} | "
        f"total: {u.total_tokens:,}"
    )


def _coerce_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0
