"""
File writing tool for nanocode.

Writes content to files. Creates new files or overwrites existing ones.
Does not create parent directories.

Example:
    >>> from nanocode.tools.write import WriteTool
    >>> tool = WriteTool()
    >>> result = tool.execute({"path": "output.txt", "content": "Hello, world!"})
    >>> print(result)
    'ok'
"""

from __future__ import annotations

from typing import Any, ClassVar

from nanocode.tools.base import BaseTool
from nanocode.tools.registry import register_tool


@register_tool
class WriteTool(BaseTool):
    """
    Tool for writing content to files.

    Creates new files or overwrites existing files with the provided content.
    Does not automatically create parent directories - this must be done
    beforehand if needed.

    Attributes:
        name: Always "write".
        description: Human-readable description for the AI.
        parameters: Parameter schema with path and content.

    Example:
        >>> tool = WriteTool()
        >>> tool.execute({
        ...     "path": "new_file.txt",
        ...     "content": "File contents here"
        ... })
        'ok'
    """

    name = "write"
    description = (
        "Write content to file (overwrites if it exists; "
        "does not create parent directories)."
    )
    parameters = {
        "path": "string",
        "content": "string",
    }

    def execute(self, args: dict[str, Any]) -> str:
        """
        Write content to a file.

        Args:
            args: Dictionary containing:
                - path: Path to the file to write (required)
                - content: Content to write (required)

        Returns:
            "ok" on success, or an error string on failure.
        """
        path = args["path"]
        content = args["content"]

        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            return "ok"
        except OSError as e:
            return f"error: {e}"
        except Exception as e:
            return f"error: {type(e).__name__}: {e}"
