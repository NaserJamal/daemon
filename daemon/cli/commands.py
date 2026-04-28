"""Slash commands and exit aliases for the REPL."""

from __future__ import annotations

from typing import Any

from daemon.cli.io import GREEN, RESET
from daemon.core.prompt import get_default_system_prompt

QUIT_INPUTS = {"/q", "/quit", "/exit", "exit"}


def handle(user_input: str, messages: list[dict[str, Any]]) -> bool | None:
    """Handle a slash command. Returns:

    - False: user wants to quit
    - True: command was handled; resume the REPL loop
    - None: not a command; caller should treat input as a normal message
    """
    if user_input in QUIT_INPUTS:
        return False
    if user_input in ("/c", "/clear"):
        messages[:] = [{"role": "system", "content": get_default_system_prompt()}]
        print(f"{GREEN}⏺ Cleared conversation{RESET}")
        return True
    return None
