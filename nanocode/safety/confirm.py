"""
User confirmation prompts for nanocode.

Handles interactive confirmation for dangerous operations,
with support for YOLO mode bypass.

Example:
    >>> from nanocode.safety.confirm import confirm
    >>> # Would prompt user in real usage
    >>> # confirm("rm -rf /", "rm")
"""

from __future__ import annotations

import sys
from typing import TextIO

from nanocode.core.config import get_settings
from nanocode.safety.danger import DangerDetector


# ANSI color codes for terminal output
RESET = "\033[0m"
BOLD = "\033[1m"
RED = "\033[31m"


class ConfirmPrompt:
    """
    Handles user confirmation prompts for dangerous operations.

    Displays a warning with the command and reason, then prompts
    for user confirmation. Supports YOLO mode for bypassing.

    Attributes:
        input_func: Function to use for input (injectable for testing).
        output_func: Function to use for output (injectable for testing).

    Example:
        >>> prompt = ConfirmPrompt()
        >>> if prompt.should_proceed("rm -rf /", "rm"):
        ...     execute_dangerous_command()
    """

    def __init__(
        self,
        input_func: callable[[str], str] | None = None,
        output_func: callable[[str], None] | None = None,
    ) -> None:
        """
        Initialize the confirmation prompt handler.

        Args:
            input_func: Optional function for getting user input.
                       Defaults to builtins.input.
            output_func: Optional function for output. Defaults to print.
        """
        self._input_func = input_func
        self._output_func = output_func

    @property
    def input_func(self) -> callable[[str], str]:
        """Get the input function."""
        if self._input_func is None:
            return input
        return self._input_func

    @property
    def output_func(self) -> callable[[str], None]:
        """Get the output function."""
        if self._output_func is None:
            return print
        return self._output_func

    def _print(self, message: str) -> None:
        """Print a message using the output function."""
        self.output_func(message)

    def _get_input(self, prompt: str) -> str:
        """Get input using the input function."""
        return self.input_func(prompt)

    def should_proceed(
        self,
        command: str,
        reason: str,
        detector: DangerDetector | None = None,
    ) -> bool:
        """
        Determine if execution should proceed.

        Args:
            command: The command that was flagged.
            reason: The reason it was flagged.
            detector: Optional detector (not currently used).

        Returns:
            True if execution should proceed, False otherwise.
        """
        settings = get_settings()
        if settings.yolo:
            return True

        return self.prompt(command, reason)

    def prompt(self, command: str, reason: str) -> bool:
        """
        Display the confirmation prompt and get user response.

        Args:
            command: The dangerous command.
            reason: The reason for the warning.

        Returns:
            True if user approved, False otherwise.
        """
        self._print(f"\n{RED}⚠  Dangerous command detected ({reason}):{RESET}")
        self._print(f"  {BOLD}{command}{RESET}")

        try:
            answer = self._get_input(f"{RED}Approve? [y/N] {RESET}").strip().lower()
        except (KeyboardInterrupt, EOFError):
            return False

        return answer in ("y", "yes")

    def explain_risk(self, reason: str) -> str:
        """
        Get an explanation of a risk category.

        Args:
            reason: The risk reason label.

        Returns:
            A human-readable explanation of the risk.
        """
        explanations: dict[str, str] = {
            "rm": "This command deletes files. The -r flag makes it recursive, -f forces deletion.",
            "rmdir": "This command removes empty directories.",
            "mv to /": "Moving files to root may cause system issues or data loss.",
            "dd": "This command writes directly to disks/partitions - data loss is immediate.",
            "mkfs": "This command formats partitions, destroying all data.",
            "system power": "This command shuts down or reboots the system.",
            "kill -9": "This forcefully kills processes without cleanup.",
            "fork bomb": "This creates unlimited processes until system crashes.",
            "raw disk write": "Writing directly to disk devices causes data loss.",
            "overwrite /etc": "Modifying /etc can break system configuration.",
            "recursive chmod": "Changing permissions recursively may break security.",
            "recursive chown": "Changing ownership recursively may grant unintended access.",
            "sudo": "This command runs with elevated privileges.",
            "git reset --hard": "This discards all uncommitted changes.",
            "git clean -f": "This removes untracked files permanently.",
            "git force push": "This overwrites remote history, potentially losing work.",
            "git branch -D": "This permanently deletes a branch.",
            "git checkout .": "This discards all local changes.",
            "git restore .": "This reverts all local changes to last commit.",
            "SQL drop": "This permanently deletes database objects.",
            "SQL truncate": "This deletes all rows from a table.",
            "docker destructive": "This removes containers, images, or volumes.",
            "kubectl delete": "This deletes Kubernetes resources.",
            "terraform destroy/apply": "This creates or destroys infrastructure.",
            "npm publish": "This publishes a package to the registry.",
            "curl | sh": "Running downloaded scripts without verification is dangerous.",
            "eval": "This executes arbitrary code, which is security risky.",
        }
        return explanations.get(reason, f"Unknown risk: {reason}")


def confirm(cmd: str, reason: str) -> bool:
    """
    Display a confirmation prompt for a dangerous command.

    This is a convenience function using the global ConfirmPrompt.

    Args:
        cmd: The dangerous command.
        reason: The reason for the warning.

    Returns:
        True if the user approved execution.
    """
    return ConfirmPrompt().prompt(cmd, reason)


def confirm_or_bypass(
    cmd: str,
    reason: str,
    yolo: bool | None = None,
) -> bool:
    """
    Confirm a command or bypass if YOLO mode is enabled.

    Args:
        cmd: The dangerous command.
        reason: The reason for the warning.
        yolo: Whether to bypass. Uses settings if None.

    Returns:
        True if execution should proceed.
    """
    if yolo is None:
        settings = get_settings()
        yolo = settings.yolo

    if yolo:
        return True

    return confirm(cmd, reason)
