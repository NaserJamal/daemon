"""Write tool: overwrite a file with the given content."""

from __future__ import annotations

from typing import Any

from daemon.tools.base import BaseTool
from daemon.tools.registry import register_tool


@register_tool
class WriteTool(BaseTool):
    name = "write"
    description = (
        "Write content to file (overwrites if it exists; does not create parent directories)."
    )
    parameters = {"path": "string", "content": "string"}

    def execute(self, args: dict[str, Any]) -> str:
        with open(args["path"], "w", encoding="utf-8") as f:
            f.write(args["content"])
        return "ok"
