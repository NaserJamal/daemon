"""Interactive configuration flow and `daemon config ...` subcommands."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys

from daemon.cli.io import BOLD, DIM, GREEN, RED, RESET
from daemon.core import user_config
from daemon.core.config import reset_settings


def _prompt(label: str, current: str, *, secret: bool = False) -> str:
    """Prompt for a value, showing the current value and accepting blank as 'keep'."""
    shown = user_config.mask_secret(current) if secret else current
    suffix = f" {DIM}[{shown}]{RESET}" if current else ""
    try:
        value = input(f"{BOLD}{label}{RESET}{suffix}: ").strip()
    except EOFError:
        return current
    return value or current


def _prompt_bool(label: str, current: bool) -> bool:
    """Prompt for yes/no, showing the current value and accepting blank as 'keep'."""
    default = "y" if current else "n"
    try:
        raw = input(f"{BOLD}{label}{RESET} {DIM}[{default}]{RESET}: ").strip().lower()
    except EOFError:
        return current
    if not raw:
        return current
    return raw in ("y", "yes", "1", "true", "on")


def run_configure() -> int:
    """Walk the user through setting BASE_URL / API_KEY / MODEL_NAME. Returns exit code."""
    existing = user_config.load()
    print(f"{BOLD}daemon configuration{RESET}")
    print(f"{DIM}Stored at: {user_config.config_path()}{RESET}")
    print(f"{DIM}Press Enter to keep the current value.{RESET}\n")

    base_url = _prompt(
        "BASE_URL",
        existing.get("BASE_URL", "https://api.openai.com/v1"),
    )
    api_key = _prompt("API_KEY", existing.get("API_KEY", ""), secret=True)
    model_name = _prompt("MODEL_NAME", existing.get("MODEL_NAME", "gpt-4o-mini"))
    yolo_current = existing.get("YOLO", "").lower() in user_config.TRUTHY
    yolo = _prompt_bool("YOLO (skip dangerous-command confirmations)", yolo_current)

    if not api_key:
        print(f"\n{RED}API_KEY is required.{RESET}")
        return 1

    path = user_config.save(
        {
            "BASE_URL": base_url.rstrip("/"),
            "API_KEY": api_key,
            "MODEL_NAME": model_name,
            "YOLO": "true" if yolo else "false",
        }
    )
    reset_settings()
    print(f"\n{GREEN}✓ Saved to {path}{RESET}")
    return 0


def _show() -> int:
    cfg = user_config.load()
    path = user_config.config_path()
    if not cfg:
        print(f"{DIM}No config at {path}. Run `daemon configure` to create one.{RESET}")
        return 0
    print(f"{DIM}{path}{RESET}")
    for key in user_config.KNOWN_KEYS:
        value = cfg.get(key, "")
        shown = user_config.mask_secret(value) if key == "API_KEY" else value
        print(f"  {key}={shown}")
    return 0


def run_yolo(argv: list[str]) -> int:
    """Toggle YOLO, or set it explicitly with `daemon yolo on|off`. Persists to config."""
    cfg = user_config.load()
    current = cfg.get("YOLO", "").lower() in user_config.TRUTHY

    if not argv:
        new_value = not current
    else:
        arg = argv[0].lower()
        if arg in ("on", "true", "1", "yes", "enable"):
            new_value = True
        elif arg in ("off", "false", "0", "no", "disable"):
            new_value = False
        elif arg == "toggle":
            new_value = not current
        else:
            print(f"{RED}Unknown: daemon yolo {arg}{RESET}")
            print("Usage: daemon yolo [on|off|toggle]")
            return 2

    cfg["YOLO"] = "true" if new_value else "false"
    user_config.save(cfg)
    reset_settings()
    state = f"{RED}ON{RESET}" if new_value else f"{GREEN}OFF{RESET}"
    print(f"YOLO is now {state}")
    return 0


def _path() -> int:
    print(user_config.config_path())
    return 0


def _edit() -> int:
    path = user_config.config_path()
    if not path.exists():
        print(f"{DIM}No config yet. Creating empty file at {path}.{RESET}")
        user_config.save({})
    editor = os.environ.get("VISUAL") or os.environ.get("EDITOR")
    if not editor:
        editor = (
            "notepad"
            if sys.platform == "win32"
            else (shutil.which("nano") or shutil.which("vi") or "vi")
        )
    try:
        subprocess.call([editor, str(path)])
    except OSError as err:
        print(f"{RED}Could not launch editor ({editor}): {err}{RESET}")
        return 1
    reset_settings()
    return 0


def handle_subcommand(argv: list[str]) -> int | None:
    """Dispatch `daemon configure` and `daemon config ...`. Returns exit code or None."""
    if not argv:
        return None
    cmd = argv[0]
    if cmd == "configure":
        return run_configure()
    if cmd == "yolo":
        return run_yolo(argv[1:])
    if cmd == "config":
        sub = argv[1] if len(argv) > 1 else "show"
        if sub == "show":
            return _show()
        if sub == "path":
            return _path()
        if sub == "edit":
            return _edit()
        if sub in ("set", "configure"):
            return run_configure()
        print(f"{RED}Unknown: daemon config {sub}{RESET}")
        print("Usage: daemon config {show|path|edit}")
        return 2
    return None
