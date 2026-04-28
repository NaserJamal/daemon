"""Persistent user configuration in the OS-appropriate config directory.

Layout (per-OS):
- Linux:   $XDG_CONFIG_HOME/daemon/config  (default: ~/.config/daemon/config)
- macOS:   ~/Library/Application Support/daemon/config
- Windows: %APPDATA%/daemon/config         (default: ~/AppData/Roaming/daemon/config)

File format is the same KEY=VALUE syntax used by .env files so users can hand-edit
it without surprises. Values may be quoted; lines starting with `#` are ignored.
"""

from __future__ import annotations

import os
import stat
import sys
from pathlib import Path

APP_NAME = "daemon"
KNOWN_KEYS = ("BASE_URL", "API_KEY", "MODEL_NAME", "YOLO")

TRUTHY = ("1", "true", "yes", "on")


def config_dir() -> Path:
    """Return the user-config directory for this OS (not created)."""
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
        return Path(base) / APP_NAME
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / APP_NAME
    base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / APP_NAME


def config_path() -> Path:
    """Return the full path to the user config file (not created)."""
    return config_dir() / "config"


def load() -> dict[str, str]:
    """Read the user config file, returning a dict of KEY=VALUE pairs.

    Returns an empty dict if the file does not exist.
    """
    path = config_path()
    if not path.is_file():
        return {}
    out: dict[str, str] = {}
    with path.open(encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key, value = key.strip(), value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
                value = value[1:-1]
            out[key] = value
    return out


def save(values: dict[str, str]) -> Path:
    """Write `values` to the user config file, creating parents as needed.

    On Unix, the file is chmod 0600 so the API key is not world-readable.
    Returns the path written.
    """
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# daemon user configuration", "# Edit by hand or run `daemon configure`.", ""]
    for key in KNOWN_KEYS:
        value = values.get(key, "")
        if not value:
            continue
        if '"' in value:
            raise ValueError(f"{key} cannot contain a double-quote character")
        lines.append(f'{key}="{value}"')
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    if sys.platform != "win32":
        try:
            path.chmod(stat.S_IRUSR | stat.S_IWUSR)
        except OSError:
            pass
    return path


def mask_secret(value: str) -> str:
    """Return a redacted preview of a secret (last 4 chars visible)."""
    if not value:
        return ""
    if len(value) <= 4:
        return "*" * len(value)
    return "*" * (len(value) - 4) + value[-4:]
