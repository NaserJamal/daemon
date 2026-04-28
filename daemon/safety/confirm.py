"""Interactive confirmation prompt for dangerous commands."""

from __future__ import annotations

from daemon.core.config import get_settings

RESET = "\033[0m"
BOLD = "\033[1m"
RED = "\033[31m"


def confirm(cmd: str, reason: str) -> bool:
    """Prompt the user to approve a flagged command.

    Returns True if the user types y/yes, False otherwise (including
    on Ctrl+C / EOF, which are treated as a "no"). Bypassed when YOLO
    mode is enabled in settings.
    """
    if get_settings().yolo:
        return True

    print(f"\n{RED}⚠  Dangerous command detected ({reason}):{RESET}")
    print(f"  {BOLD}{cmd}{RESET}")
    try:
        answer = input(f"{RED}Approve? [y/N] {RESET}").strip().lower()
    except (KeyboardInterrupt, EOFError):
        return False
    return answer in ("y", "yes")
