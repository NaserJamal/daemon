"""Terminal output helpers: ANSI color constants and small formatting functions."""

from __future__ import annotations

import os
import re

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
BLUE = "\033[34m"
CYAN = "\033[36m"
GREEN = "\033[32m"
RED = "\033[31m"


def separator() -> str:
    """Return a horizontal rule sized to the terminal (max 80 cols)."""
    try:
        cols = min(os.get_terminal_size().columns, 80)
    except OSError:
        cols = 80
    return f"{DIM}{'─' * cols}{RESET}"


def render_markdown(text: str) -> str:
    """Apply lightweight bold rendering for **text**. Other markup is left intact."""
    return re.sub(r"\*\*(.+?)\*\*", f"{BOLD}\\1{RESET}", text)
