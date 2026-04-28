"""System prompt generation."""

from __future__ import annotations

import os


def get_default_system_prompt() -> str:
    """Return the default system prompt with the current working directory."""
    return f"You are a concise coding assistant operating in a terminal.\ncwd: {os.getcwd()}"
