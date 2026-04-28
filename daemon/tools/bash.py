"""Bash tool: shell command execution with timeout and danger gating."""

from __future__ import annotations

import subprocess
import threading
from typing import Any

from daemon.core.config import get_settings
from daemon.safety.confirm import confirm
from daemon.safety.danger import danger_reason
from daemon.tools.base import BaseTool
from daemon.tools.registry import register_tool

DIM = "\033[2m"
RESET = "\033[0m"


@register_tool
class BashTool(BaseTool):
    name = "bash"
    description = (
        "Run a shell command in the harness cwd. stderr is merged into stdout. "
        "Killed after `timeout` seconds (default 120, pass 0 to disable for "
        "long-running commands)."
    )
    parameters = {"cmd": "string", "timeout": "integer?"}

    def execute(self, args: dict[str, Any]) -> str:
        settings = get_settings()
        cmd = args["cmd"]

        if not settings.yolo:
            reason = danger_reason(cmd)
            if reason and not confirm(cmd, reason):
                return "error: user denied execution"

        timeout = max(0, args.get("timeout", settings.bash_timeout))
        proc = subprocess.Popen(
            cmd, shell=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        )
        timer = threading.Timer(timeout, proc.kill) if timeout else None
        if timer:
            timer.start()

        lines: list[str] = []
        try:
            assert proc.stdout is not None
            for line in proc.stdout:
                print(f"  {DIM}│ {line.rstrip()}{RESET}", flush=True)
                lines.append(line)
        finally:
            if timer:
                timer.cancel()
            proc.wait()

        out = "".join(lines).strip() or "(empty)"
        if proc.returncode < 0:
            out += f"\n(killed by signal {-proc.returncode}; may be {timeout}s timeout)"
        return out
