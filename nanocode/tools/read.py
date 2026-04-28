"""
File reading tool for nanocode.

Reads text files with line numbers, supporting offset and limit
for pagination. Skips binary files automatically.

Example:
    >>> from nanocode.tools.read import ReadTool
    >>> tool = ReadTool()
    >>> result = tool.execute({"path": "example.py", "offset": 1, "limit": 50})
"""

from __future__ import annotations

import os
from typing import Any, ClassVar

from nanocode.core.config import get_settings
from nanocode.tools.base import BaseTool
from nanocode.tools.registry import register_tool


@register_tool
class ReadTool(BaseTool):
    """
    Tool for reading text files with line numbers.

    Supports pagination through offset and limit parameters.
    Automatically detects and rejects binary files.
    Lines are truncated to a maximum length to prevent huge outputs.

    Attributes:
        name: Always "read".
        description: Human-readable description for the AI.
        parameters: Parameter schema with path, offset, and limit.

    Example:
        >>> tool = ReadTool()
        >>> tool.execute({"path": "file.txt", "offset": 1, "limit": 100})
        '   1| First line of file\\n   2| Second line\\n...'
    """

    name = "read"
    description = (
        "Read a text file with line numbers. offset is 1-indexed; "
        "default limit 2000 lines. Output format is 'N| <content>' - "
        "the 'N| ' prefix is NOT part of the file content."
    )
    parameters = {
        "path": "string",
        "offset": "integer?",
        "limit": "integer?",
    }

    def execute(self, args: dict[str, Any]) -> str:
        """
        Read a file with pagination support.

        Args:
            args: Dictionary containing:
                - path: Path to the file to read (required)
                - offset: 1-indexed starting line (optional, default 1)
                - limit: Maximum lines to read (optional, default 2000)

        Returns:
            String containing the file contents with line numbers.
            Returns an error string if the file cannot be read.
        """
        settings = get_settings()
        max_lines = settings.max_lines
        max_line_len = settings.max_line_len

        path = args["path"]
        offset = max(1, args.get("offset", 1))
        limit = args.get("limit", max_lines)

        # Check if file is binary
        try:
            with open(path, "rb") as f:
                if b"\x00" in f.read(4096):
                    return f"error: {path} looks binary"
        except OSError as e:
            return f"error: {e}"

        # Read file with pagination
        selected = []
        total = 0

        try:
            with open(path, encoding="utf-8", errors="replace") as f:
                for total, line in enumerate(f, 1):
                    if offset <= total < offset + limit:
                        line = line.rstrip("\n")
                        # Truncate long lines
                        if len(line) > max_line_len:
                            line = line[:max_line_len] + "... (line truncated)"
                        selected.append(f"{total:4}| {line}")
        except OSError as e:
            return f"error: {e}"

        # Check for valid offset
        if total and offset > total:
            return f"error: offset {offset} exceeds file length ({total} lines)"

        # Build footer with pagination info
        end = offset + len(selected) - 1
        if end >= total:
            footer = f"\n(end of file - {total} lines total)"
        else:
            footer = f"\n(showing {offset}-{end} of {total}, use offset={end + 1} to continue)"

        return "\n".join(selected) + footer
