"""
Regex search tool for nanocode.

Searches files for Python-style regex patterns, skipping binaries
and hidden directories. Results are capped at a configurable limit.

Example:
    >>> from nanocode.tools.grep import GrepTool
    >>> tool = GrepTool()
    >>> result = tool.execute({"pattern": "def.*\\(", "path": "."})
"""

from __future__ import annotations

import os
import re
from typing import Any, ClassVar

from nanocode.core.config import get_settings
from nanocode.tools.base import BaseTool
from nanocode.tools.registry import register_tool


@register_tool
class GrepTool(BaseTool):
    """
    Tool for searching files with regex patterns.

    Recursively searches files in a directory for matches to a
    Python-style regex pattern. Skips binary files and hidden directories
    (those starting with '.'). Results are limited to prevent huge outputs.

    Attributes:
        name: Always "grep".
        description: Human-readable description for the AI.
        parameters: Parameter schema with pattern and path.

    Example:
        >>> tool = GrepTool()
        >>> tool.execute({"pattern": "TODO", "path": "src/"})
        'src/main.py:5:TODO: implement feature\\nsrc/utils.py:12:TODO: fix bug'
    """

    name = "grep"
    description = (
        "Search files under `path` (default '.') for a Python regex. "
        "Skips binaries and hidden dirs (.git, .venv, etc). "
        "Caps at 50 matches."
    )
    parameters = {
        "pattern": "string",
        "path": "string?",
    }

    def execute(self, args: dict[str, Any]) -> str:
        """
        Search files for a regex pattern.

        Args:
            args: Dictionary containing:
                - pattern: Python regex pattern to search for (required)
                - path: Directory to search in (optional, default ".")

        Returns:
            Newline-separated list of matches in format:
            "path:line_number:content"
            Or "none" if no matches found.
            If capped, includes truncation notice.
        """
        settings = get_settings()
        grep_cap = settings.grep_cap

        pattern = re.compile(args["pattern"])
        path = args.get("path", ".")

        hits: list[str] = []

        for dirpath, dirnames, filenames in os.walk(path):
            # Skip hidden directories
            dirnames[:] = [d for d in dirnames if not d.startswith(".")]

            for name in filenames:
                file_path = os.path.join(dirpath, name)

                try:
                    # Check for binary files
                    with open(file_path, "rb") as f:
                        if b"\x00" in f.read(4096):
                            continue
                except OSError:
                    continue

                try:
                    with open(file_path, encoding="utf-8", errors="replace") as f:
                        for n, line in enumerate(f, 1):
                            if pattern.search(line):
                                hits.append(f"{file_path}:{n}:{line.rstrip()}")
                                if len(hits) >= grep_cap:
                                    return (
                                        "\n".join(hits)
                                        + f"\n(truncated at {grep_cap} matches)"
                                    )
                except OSError:
                    continue

        if not hits:
            return "none"

        return "\n".join(hits)
