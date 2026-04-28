"""Glob tool: filesystem pattern matching, sorted newest-first."""

from __future__ import annotations

import glob as globlib
import os
from typing import Any

from daemon.tools.base import BaseTool
from daemon.tools.registry import register_tool


def _mtime(path: str) -> float:
    try:
        return os.path.getmtime(path)
    except OSError:
        return 0


@register_tool
class GlobTool(BaseTool):
    name = "glob"
    description = (
        "Find files matching a glob pattern (e.g. '**/*.py'), sorted newest first. "
        "`pattern` is joined onto `path` (default '.')."
    )
    parameters = {"pattern": "string", "path": "string?"}

    def execute(self, args: dict[str, Any]) -> str:
        pattern = os.path.join(args.get("path", "."), args["pattern"])
        files = globlib.glob(pattern, recursive=True)
        if not files:
            return "none"
        return "\n".join(sorted(files, key=_mtime, reverse=True))
