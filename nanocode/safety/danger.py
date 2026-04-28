"""
Danger pattern detection for nanocode.

Detects potentially harmful bash commands using regex patterns.
This is best-effort detection - a determined actor can obfuscate commands.

Example:
    >>> from nanocode.safety.danger import danger_reason
    >>> danger_reason("rm -rf /")
    'rm'
    >>> danger_reason("ls -la")
    None
"""

from __future__ import annotations

import re
from typing import Pattern

from nanocode.core.config import Settings, get_settings


# Danger patterns that warrant human confirmation before bash execution.
# Format: (regex_pattern, label_description)
DANGER_PATTERNS: list[tuple[str, str]] = [
    (r"\brm\s+(-[a-zA-Z]*[rRfF][a-zA-Z]*\s+)?", "rm"),
    (r"\brmdir\b", "rmdir"),
    (r"\bmv\s+[^|;&]*\s+/(?:\s|$)", "mv to /"),
    (r"\bdd\b.*\bof=", "dd"),
    (r"\bmkfs\.[a-z0-9]+\b", "mkfs"),
    (r"\b(shutdown|reboot|halt|poweroff)\b", "system power"),
    (r"\bkill(all)?\s+-9\b", "kill -9"),
    (r":\(\)\s*\{.*\}\s*;", "fork bomb"),
    (r">\s*/dev/(sd[a-z]|nvme|disk)", "raw disk write"),
    (r">\s*/etc/", "overwrite /etc"),
    (r"\bchmod\s+-R\b", "recursive chmod"),
    (r"\bchown\s+-R\b", "recursive chown"),
    (r"\bsudo\b", "sudo"),
    (r"\bgit\s+reset\s+--hard\b", "git reset --hard"),
    (r"\bgit\s+clean\s+-[a-z]*f", "git clean -f"),
    (r"\bgit\s+push\s+(-[a-zA-Z]*f|--force)", "git force push"),
    (r"\bgit\s+branch\s+-D\b", "git branch -D"),
    (r"\bgit\s+checkout\s+\.", "git checkout ."),
    (r"\bgit\s+restore\s+\.", "git restore ."),
    (r"\bdrop\s+(table|database|schema)\b", "SQL drop"),
    (r"\btruncate\s+table\b", "SQL truncate"),
    (r"\bdocker\s+(rm|rmi|system\s+prune|volume\s+rm)", "docker destructive"),
    (r"\bkubectl\s+delete\b", "kubectl delete"),
    (r"\bterraform\s+(destroy|apply)\b", "terraform destroy/apply"),
    (r"\bnpm\s+publish\b", "npm publish"),
    (r"\b(curl|wget)\b[^|;&]*\|\s*(sh|bash|zsh)\b", "curl | sh"),
    (r"\beval\b", "eval"),
]


class DangerDetector:
    """
    Detects potentially dangerous commands for safety confirmation.

    Uses regex patterns to identify commands that could cause data loss,
    system changes, or other harmful effects. Detection is best-effort
    and should not be considered foolproof.

    Attributes:
        patterns: List of (compiled_pattern, label) tuples.
        categories: Dictionary mapping category names to pattern lists.

    Example:
        >>> detector = DangerDetector()
        >>> reason = detector.detect("rm -rf /")
        >>> print(reason)
        'rm'
    """

    def __init__(
        self,
        patterns: list[tuple[str, str]] | None = None,
        compiled: bool = False,
    ) -> None:
        """
        Initialize the danger detector.

        Args:
            patterns: Optional list of (pattern, label) tuples.
                     Uses default patterns if None.
            compiled: Whether to compile patterns immediately.
        """
        self._patterns: list[tuple[Pattern[str], str]]
        if patterns is None:
            patterns = DANGER_PATTERNS

        if compiled:
            self._patterns = [
                (re.compile(pattern), label) for pattern, label in patterns
            ]
        else:
            # Store raw patterns, compile lazily
            self._patterns = patterns  # type: ignore[assignment]

    def _ensure_compiled(self) -> None:
        """Ensure patterns are compiled (lazy compilation)."""
        if self._patterns and isinstance(self._patterns[0], tuple):
            first = self._patterns[0]
            if isinstance(first[0], str):
                self._patterns = [
                    (re.compile(pattern), label)  # type: ignore[misc]
                    for pattern, label in self._patterns  # type: ignore[misc]
                ]

    def detect(self, command: str) -> str | None:
        """
        Detect danger in a command string.

        Args:
            command: The bash command to check.

        Returns:
            The label of the detected danger pattern, or None if safe.
        """
        self._ensure_compiled()
        for pattern, label in self._patterns:  # type: ignore[union-attr]
            if pattern.search(command):  # type: ignore[union-attr]
                return label
        return None

    def add_pattern(self, pattern: str, label: str) -> None:
        """
        Add a new danger pattern.

        Args:
            pattern: Regex pattern to match.
            label: Human-readable label for the danger.
        """
        self._ensure_compiled()
        compiled = re.compile(pattern)
        self._patterns.append((compiled, label))  # type: ignore[union-attr]

    def remove_pattern(self, label: str) -> int:
        """
        Remove danger patterns by label.

        Args:
            label: The label of patterns to remove.

        Returns:
            Number of patterns removed.
        """
        self._ensure_compiled()
        original_len = len(self._patterns)  # type: ignore[union-attr]
        self._patterns = [
            (p, l) for p, l in self._patterns if l != label  # type: ignore[misc]
        ]
        return original_len - len(self._patterns)  # type: ignore[union-attr]

    def is_safe(self, command: str) -> bool:
        """
        Check if a command is safe (no danger detected).

        Args:
            command: The bash command to check.

        Returns:
            True if the command is considered safe.
        """
        return self.detect(command) is None

    def get_categories(self) -> dict[str, list[str]]:
        """
        Get danger pattern categories.

        Returns:
            Dictionary mapping category names to pattern labels.
        """
        self._ensure_compiled()
        categories: dict[str, list[str]] = {}
        for _, label in self._patterns:  # type: ignore[union-attr]
            # Extract category from label (e.g., "git force push" -> "git")
            category = label.split()[0] if label else "unknown"
            if category not in categories:
                categories[category] = []
            if label not in categories[category]:
                categories[category].append(label)
        return categories


def danger_reason(cmd: str) -> str | None:
    """
    Detect danger in a command using global patterns.

    This is a convenience function that uses the default DangerDetector.

    Args:
        cmd: The bash command to check.

    Returns:
        The danger label, or None if the command is considered safe.
    """
    return DangerDetector().detect(cmd)


# Module-level singleton detector
_detector: DangerDetector | None = None


def get_detector() -> DangerDetector:
    """
    Get the module-level danger detector singleton.

    Returns:
        The singleton DangerDetector instance.
    """
    global _detector
    if _detector is None:
        _detector = DangerDetector()
    return _detector
