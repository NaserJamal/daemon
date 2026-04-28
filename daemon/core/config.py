"""Runtime configuration loaded from the user config file.

All settings (including the YOLO safety flag) live in the per-user config
file managed by `daemon configure` (see `daemon.core.user_config` for the
platform-specific location). This is the only source of truth — there is
no env-var or `.env` fallback.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from daemon.core import user_config


class Settings(BaseModel):
    """Runtime configuration. Defaults can be overridden via the user config file."""

    model_config = ConfigDict(protected_namespaces=())

    base_url: str = Field(default="https://api.openai.com/v1")
    api_key: str = Field(default="")
    model_name: str = Field(default="gpt-4o-mini")
    max_lines: int = Field(default=2000)
    max_line_len: int = Field(default=2000)
    bash_timeout: int = Field(default=120)
    grep_cap: int = Field(default=50)
    yolo: bool = Field(default=False)

    @classmethod
    def from_env(cls) -> Settings:
        """Build Settings from the user config file."""
        cfg = user_config.load()
        return cls(
            base_url=cfg.get("BASE_URL", cls.model_fields["base_url"].default).rstrip("/"),
            api_key=cfg.get("API_KEY", ""),
            model_name=cfg.get("MODEL_NAME", cls.model_fields["model_name"].default),
            yolo=cfg.get("YOLO", "").lower() in user_config.TRUTHY,
        )


_settings: Settings | None = None


def get_settings() -> Settings:
    """Return a cached Settings instance, building from the config file on first call."""
    global _settings
    if _settings is None:
        _settings = Settings.from_env()
    return _settings


def reset_settings() -> None:
    """Reset the cached Settings (for tests and post-reconfigure)."""
    global _settings
    _settings = None
