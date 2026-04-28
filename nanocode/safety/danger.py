"""Best-effort detection of dangerous shell commands.

Detection is regex-based and intentionally conservative; a determined
caller can always obfuscate around it. The goal is to surface obvious
foot-guns to the user, not to provide airtight sandboxing.
"""

from __future__ import annotations

import re

# (regex, label). Order doesn't matter — first match wins.
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

_COMPILED: list[tuple[re.Pattern[str], str]] = [
    (re.compile(pattern), label) for pattern, label in DANGER_PATTERNS
]


def danger_reason(cmd: str) -> str | None:
    """Return the label of the first matching danger pattern, or None."""
    for pattern, label in _COMPILED:
        if pattern.search(cmd):
            return label
    return None
