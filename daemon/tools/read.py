"""Read tool: paginated, line-numbered text file reader."""

from __future__ import annotations

from typing import Any

from daemon.core.config import get_settings
from daemon.tools.base import BaseTool
from daemon.tools.registry import register_tool


@register_tool
class ReadTool(BaseTool):
    name = "read"
    description = (
        "Read a text file with line numbers. offset is 1-indexed; default limit 2000 lines. "
        "Output format is 'N| <content>' - the 'N| ' prefix is NOT part of the file content."
    )
    parameters = {"path": "string", "offset": "integer?", "limit": "integer?"}

    def execute(self, args: dict[str, Any]) -> str:
        settings = get_settings()
        path = args["path"]
        offset = max(1, args.get("offset", 1))
        limit = args.get("limit", settings.max_lines)
        max_line_len = settings.max_line_len

        # Reject obvious binary files cheaply via NUL sniff.
        try:
            with open(path, "rb") as f:
                if b"\x00" in f.read(4096):
                    return f"error: {path} looks binary"
        except OSError as e:
            return f"error: {e}"

        selected: list[str] = []
        total = 0
        try:
            with open(path, encoding="utf-8", errors="replace") as f:
                for total, line in enumerate(f, 1):
                    if offset <= total < offset + limit:
                        line = line.rstrip("\n")
                        if len(line) > max_line_len:
                            line = line[:max_line_len] + "... (line truncated)"
                        selected.append(f"{total:4}| {line}")
        except OSError as e:
            return f"error: {e}"

        if total and offset > total:
            return f"error: offset {offset} exceeds file length ({total} lines)"

        end = offset + len(selected) - 1
        if end >= total:
            footer = f"\n(end of file - {total} lines total)"
        else:
            footer = f"\n(showing {offset}-{end} of {total}, use offset={end + 1} to continue)"
        return "\n".join(selected) + footer
