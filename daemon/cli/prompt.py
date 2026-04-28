"""Multi-line input prompt with history and rich keybindings (prompt_toolkit)."""

from __future__ import annotations

import os
from pathlib import Path

from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import ANSI
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.key_binding.key_processor import KeyPressEvent

from daemon.cli.io import BLUE, BOLD, RESET

_HISTORY_PATH = Path(os.path.expanduser("~/.daemon/history"))


def _build_keybindings() -> KeyBindings:
    kb = KeyBindings()

    @kb.add("enter")
    def _submit(event: KeyPressEvent) -> None:
        buf = event.current_buffer
        text = buf.text
        # Backslash-continuation: trailing `\` becomes a newline (works in any terminal).
        if text.endswith("\\"):
            buf.delete_before_cursor(1)
            buf.insert_text("\n")
            return
        buf.validate_and_handle()

    # Alt/Opt+Enter (terminal sends ESC + CR). Most terminals can be configured
    # to send this same sequence when Shift+Enter is pressed, giving the user
    # a "Shift+Enter for newline" experience identical to Claude Code.
    @kb.add("escape", "enter")
    def _newline_alt(event: KeyPressEvent) -> None:
        event.current_buffer.insert_text("\n")

    # Double-Escape clears the current input buffer.
    @kb.add("escape", "escape")
    def _clear_input(event: KeyPressEvent) -> None:
        event.current_buffer.text = ""

    return kb


def _make_session() -> PromptSession[str]:
    _HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    return PromptSession(
        history=FileHistory(str(_HISTORY_PATH)),
        multiline=True,
        key_bindings=_build_keybindings(),
        enable_history_search=True,
        mouse_support=False,
    )


_session: PromptSession[str] | None = None


def read_input() -> str:
    """Read one (possibly multi-line) user message. Raises EOFError/KeyboardInterrupt."""
    global _session
    if _session is None:
        _session = _make_session()
    return _session.prompt(ANSI(f"{BOLD}{BLUE}❯{RESET} "))
