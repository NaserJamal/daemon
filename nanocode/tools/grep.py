"""Grep tool: recursive regex search, skipping binaries and dot-dirs."""

from __future__ import annotations

import os
import re
from typing import Any

from nanocode.core.config import get_settings
from nanocode.tools.base import BaseTool
from nanocode.tools.registry import register_tool


@register_tool
class GrepTool(BaseTool):
    name = "grep"
    description = (
        "Search files under `path` (default '.') for a Python regex. Skips binaries "
        "and hidden dirs (.git, .venv, etc). Caps at 50 matches."
    )
    parameters = {"pattern": "string", "path": "string?"}

    def execute(self, args: dict[str, Any]) -> str:
        cap = get_settings().grep_cap
        pattern = re.compile(args["pattern"])
        hits: list[str] = []

        for dirpath, dirnames, filenames in os.walk(args.get("path", ".")):
            dirnames[:] = [d for d in dirnames if not d.startswith(".")]
            for name in filenames:
                path = os.path.join(dirpath, name)
                try:
                    with open(path, "rb") as f:
                        if b"\x00" in f.read(4096):
                            continue
                    with open(path, encoding="utf-8", errors="replace") as f:
                        for n, line in enumerate(f, 1):
                            if pattern.search(line):
                                hits.append(f"{path}:{n}:{line.rstrip()}")
                                if len(hits) >= cap:
                                    return "\n".join(hits) + f"\n(truncated at {cap} matches)"
                except OSError:
                    continue
        return "\n".join(hits) or "none"
