"""
Shell execution tool for nanocode.

Executes bash commands with optional timeout and safety confirmation
for potentially dangerous operations.

Example:
    >>> from nanocode.tools.bash import BashTool
    >>> tool = BashTool()
    >>> result = tool.execute({"cmd": "ls -la", "timeout": 30})
"""

from __future__ import annotations

import subprocess
import threading
from typing import Any, ClassVar

from nanocode.core.config import get_settings
from nanocode.safety.confirm import confirm_or_bypass
from nanocode.tools.base import BaseTool
from nanocode.tools.registry import register_tool


# ANSI color codes for terminal output
DIM = "\033[2m"
RESET = "\033[0m"


@register_tool
class BashTool(BaseTool):
    """
    Tool for executing shell commands.

    Runs bash commands in the harness's working directory with
    configurable timeout. Potentially dangerous commands require
    user confirmation unless YOLO mode is enabled.

    Attributes:
        name: Always "bash".
        description: Human-readable description for the AI.
        parameters: Parameter schema with cmd and timeout.

    Example:
        >>> tool = BashTool()
        >>> result = tool.execute({"cmd": "echo hello", "timeout": 10})
        >>> print(result)
        'hello'
    """

    name = "bash"
    description = (
        "Run a shell command in the harness cwd. stderr is merged into stdout. "
        "Killed after `timeout` seconds (default 120, pass 0 to disable)."
    )
    parameters = {
        "cmd": "string",
        "timeout": "integer?",
    }

    def execute(self, args: dict[str, Any]) -> str:
        """
        Execute a bash command.

        Args:
            args: Dictionary containing:
                - cmd: The command to execute (required)
                - timeout: Timeout in seconds (optional, default 120,
                          use 0 to disable)

        Returns:
            Command output on success, error message on failure
            or user denial.
        """
        settings = get_settings()
        default_timeout = settings.bash_timeout

        cmd = args["cmd"]

        # Safety check for dangerous commands
        if not settings.yolo:
            from nanocode.safety.danger import danger_reason

            reason = danger_reason(cmd)
            if reason and not confirm_or_bypass(cmd, reason):
                return "error: user denied execution"

        # Get timeout
        timeout = max(0, args.get("timeout", default_timeout))

        # Execute command
        proc = subprocess.Popen(
            cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )

        # Set up timeout timer if needed
        timer: threading.Timer | None = None
        if timeout:
            timer = threading.Timer(timeout, proc.kill)
            timer.start()

        lines: list[str] = []

        try:
            for line in proc.stdout:  # type: ignore[union-attr]
                # Print to terminal with dimmed styling
                print(f"  {DIM}│ {line.rstrip()}{RESET}", flush=True)
                lines.append(line)
        finally:
            if timer:
                timer.cancel()
            proc.wait()

        # Build output
        out = "".join(lines).strip() or "(empty)"

        # Add timeout notice if killed
        if proc.returncode < 0:
            out += f"\n(killed by signal {-proc.returncode}; may be {timeout}s timeout)"

        return out

    def validate_timeout(self, timeout: int) -> bool:
        """
        Validate a timeout value.

        Args:
            timeout: The timeout value to validate.

        Returns:
            True if the timeout is valid (non-negative).
        """
        return timeout >= 0
