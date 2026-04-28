"""Shared pytest fixtures and global test setup."""

from __future__ import annotations

from daemon.core import config as _config

# Force YOLO so the bash tool never blocks on confirmation prompts in tests.
_config._settings = _config.Settings(yolo=True)
