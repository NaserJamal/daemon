"""
Glob pattern matching tool for nanocode.

Finds files matching glob patterns, sorted by modification time.
Searches recursively by default.

Example:
    >>> from nanocode.tools.glob import GlobTool
    >>> tool = GlobTool()
    >>> result = tool.execute({"pattern": "**/*.py"})
"""

from __future__ import annotations

import glob as globlib
import os
from typing import Any, ClassVar

from nanocode.tools.base import BaseTool
from nanocode.tools.registry import register_tool


def _mtime(path: str) -> float:
    """
    Get modification time of a file.

    Args:
        path: Path to the file.

    Returns:
        Modification timestamp, or 0 if file cannot be accessed.
    """
    try:
        return os.path.getmtime(path)
    except OSError:
        return 0


@register_tool
class GlobTool(BaseTool):
    """
    Tool for finding files by glob patterns.

    Uses Python's glob module to find files matching a pattern.
    Results are sorted by modification time (newest first).
    Supports recursive patterns like `**/*.py`.

    Attributes:
        name: Always "glob".
        description: Human-readable description for the AI.
        parameters: Parameter schema with pattern and path.

    Example:
        >>> tool = GlobTool()
        >>> tool.execute({"pattern": "**/*.py", "path": "src/"})
        'src/main.py\\nsrc/utils.py'
    """

    name = "glob"
    description = (
        "Find files matching a glob pattern (e.g. '**/*.py'), sorted newest first. "
        "`pattern` is joined onto `path` (default '.')."
    )
    parameters = {
        "pattern": "string",
        "path": "string?",
    }

    def execute(self, args: dict[str, Any]) -> str:
        """
        Find files matching a glob pattern.

        Args:
            args: Dictionary containing:
                - pattern: Glob pattern to match (required)
                - path: Base path to search from (optional, default ".")

        Returns:
            Newline-separated list of matching file paths,
            or "none" if no matches found.
        """
        pattern = os.path.join(args.get("path", "."), args["pattern"])

        try:
            files = globlib.glob(pattern, recursive=True)
        except Exception as e:
            return f"error: {type(e).__name__}: {e}"

        if not files:
            return "none"

        # Sort by modification time, newest first
        sorted_files = sorted(files, key=_mtime, reverse=True)
        return "\n".join(sorted_files)
