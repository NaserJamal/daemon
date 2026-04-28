"""Configuration loaded from environment variables (with .env support)."""

from __future__ import annotations

import os

from pydantic import BaseModel, ConfigDict, Field


def load_dotenv(path: str = ".env") -> None:
    """Load KEY=VALUE lines from a .env file into os.environ (does not overwrite)."""
    if not os.path.isfile(path):
        return
    with open(path, encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key, value = key.strip(), value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
                value = value[1:-1]
            os.environ.setdefault(key, value)


class Settings(BaseModel):
    """Runtime configuration. Defaults can be overridden via env vars or kwargs."""

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
        """Build Settings from environment variables (loading .env first)."""
        load_dotenv()
        env = os.environ
        return cls(
            base_url=env.get("BASE_URL", cls.model_fields["base_url"].default).rstrip("/"),
            api_key=env.get("API_KEY", ""),
            model_name=env.get("MODEL_NAME", cls.model_fields["model_name"].default),
            yolo=env.get("daemon_YOLO", "").lower() in ("1", "true", "yes"),
        )


_settings: Settings | None = None


def get_settings() -> Settings:
    """Return a cached Settings instance, building from env on first call."""
    global _settings
    if _settings is None:
        _settings = Settings.from_env()
    return _settings


def reset_settings() -> None:
    """Reset the cached Settings (for tests)."""
    global _settings
    _settings = None
