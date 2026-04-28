"""
Smart edit tool for nanocode.

Replaces text in files with tolerance for whitespace differences.
If the old text matches multiple locations, the AI must provide
more context or use `all=True` to replace all matches.

Example:
    >>> from nanocode.tools.edit import EditTool
    >>> tool = EditTool()
    >>> result = tool.execute({
    ...     "path": "file.txt",
    ...     "old": "hello",
    ...     "new": "hello world"
    ... })
"""

from __future__ import annotations

from typing import Any, ClassVar

from nanocode.tools.base import BaseTool
from nanocode.tools.registry import register_tool


def _find_match(text: str, old: str) -> tuple[str | None, int]:
    """
    Locate `old` in `text`. Returns (candidate_substring, occurrence_count).

    Tries: (1) exact match, (2) line-trimmed match (tolerates per-line
    leading/trailing whitespace differences). Returns (None, 0) on miss.

    Args:
        text: The full file text to search in.
        old: The text pattern to find.

    Returns:
        Tuple of (matched_text, count) where matched_text is the actual
        substring used for replacement, or (None, 0) if no match found.
    """
    if old in text:
        return old, text.count(old)

    file_lines = text.split("\n")
    old_lines = old.split("\n")
    if not old_lines or len(old_lines) > len(file_lines):
        return None, 0

    # Build target with stripped lines for comparison
    target = [l.strip() for l in old_lines]
    matches = []

    for i in range(len(file_lines) - len(old_lines) + 1):
        window = file_lines[i : i + len(old_lines)]
        if [l.strip() for l in window] == target:
            candidate = "\n".join(window)
            if candidate in text:
                matches.append(candidate)

    if not matches:
        return None, 0

    # Prefer unique matches
    unique = [c for c in matches if text.count(c) == 1]
    chosen = unique[0] if unique else matches[0]
    return chosen, text.count(chosen)


@register_tool
class EditTool(BaseTool):
    """
    Smart text replacement tool with whitespace tolerance.

    Finds and replaces text in files with tolerance for whitespace
    differences on a per-line basis. If the old text matches multiple
    locations, either more context must be provided or `all=True`
    must be passed to replace all matches.

    If `old` is empty, the file is created/overwritten with `new`.

    Attributes:
        name: Always "edit".
        description: Human-readable description for the AI.
        parameters: Parameter schema with path, old, new, and all.

    Example:
        >>> tool = EditTool()
        >>> tool.execute({
        ...     "path": "config.py",
        ...     "old": "DEBUG = True",
        ...     "new": "DEBUG = False"
        ... })
        'ok'
    """

    name = "edit"
    description = (
        "Replace `old` with `new` in file. `old` must match uniquely unless "
        "all=true. Per-line leading/trailing whitespace is tolerated. If `old` "
        "is empty, the file is created/overwritten with `new`. Never include "
        "the 'N| ' line-number prefix from read() output in `old` or `new`."
    )
    parameters = {
        "path": "string",
        "old": "string",
        "new": "string",
        "all": "boolean?",
    }

    def execute(self, args: dict[str, Any]) -> str:
        """
        Edit a file by replacing text.

        Args:
            args: Dictionary containing:
                - path: Path to the file (required)
                - old: Text to find and replace (required, use "" to create)
                - new: Replacement text (required)
                - all: Replace all matches if True (optional)

        Returns:
            "ok" on success, error string on failure.
        """
        path = args["path"]
        old = args["old"]
        new = args["new"]

        # Check for identical old and new
        if old == new:
            return "error: old and new are identical"

        # Create mode: if old is empty, create/overwrite file
        if old == "":
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(new)
                return "ok (created)"
            except OSError as e:
                return f"error: {e}"

        # Read current file content
        try:
            with open(path, encoding="utf-8") as f:
                text = f.read()
        except OSError as e:
            return f"error: {e}"

        # Find the match
        candidate, count = _find_match(text, old)

        if candidate is None:
            return "error: old not found in file"

        if count > 1 and not args.get("all"):
            return (
                f"error: old matches {count} places, "
                "add more context or pass all=true"
            )

        # Perform replacement
        n = -1 if args.get("all") else 1
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(text.replace(candidate, new, n))
            return "ok"
        except OSError as e:
            return f"error: {e}"
