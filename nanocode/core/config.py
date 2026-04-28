"""
Configuration management for nanocode using Pydantic.

Handles loading settings from environment variables with sensible defaults.
Automatically loads configuration from .env files.

Example:
    >>> from nanocode.core.config import Settings
    >>> settings = Settings()  # Loads from env/.env
    >>> print(settings.base_url)
    'https://api.openai.com/v1'
"""

from __future__ import annotations

import os
from typing import ClassVar

from pydantic import BaseModel, Field, ConfigDict


# Constants for default values - helps avoid magic strings
DEFAULT_BASE_URL: str = "https://api.openai.com/v1"
DEFAULT_MODEL_NAME: str = "gpt-4o-mini"
DEFAULT_MAX_LINES: int = 2000
DEFAULT_MAX_LINE_LEN: int = 2000
DEFAULT_BASH_TIMEOUT: int = 120
DEFAULT_GREP_CAP: int = 50


def load_dotenv(path: str = ".env") -> None:
    """
    Load KEY=VALUE lines from a .env file into os.environ (does not overwrite).

    Args:
        path: Path to the .env file. Defaults to ".env" in current directory.

    Note:
        Lines starting with '#' are treated as comments.
        Values enclosed in single or double quotes have them stripped.
        Existing environment variables are not overwritten.
    """
    if not os.path.isfile(path):
        return
    with open(path, encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key, value = key.strip(), value.strip()
            # Strip matching quotes if present
            if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
                value = value[1:-1]
            os.environ.setdefault(key, value)


class Settings(BaseModel):
    """
    Pydantic settings model for nanocode configuration.

    All settings can be overridden via environment variables or .env file.

    Attributes:
        base_url: Base URL for the API endpoint.
        api_key: API key for authentication.
        model_name: Model identifier to use.
        max_lines: Maximum lines to read from a file.
        max_line_len: Maximum characters per line.
        bash_timeout: Default timeout for bash commands in seconds.
        grep_cap: Maximum number of grep matches before truncation.
        yolo: Bypass dangerous command confirmations.

    Example:
        >>> settings = Settings(
        ...     base_url="https://api.openai.com/v1",
        ...     model_name="gpt-4o",
        ...     yolo=True
        ... )
    """

    model_config = ConfigDict(protected_namespaces=())

    base_url: str = Field(
        default=DEFAULT_BASE_URL,
        description="Base URL for the API endpoint",
    )
    api_key: str = Field(
        default="",
        description="API key for authentication",
    )
    model_name: str = Field(
        default=DEFAULT_MODEL_NAME,
        description="Model identifier to use",
    )
    max_lines: int = Field(
        default=DEFAULT_MAX_LINES,
        description="Maximum lines to read from a file",
    )
    max_line_len: int = Field(
        default=DEFAULT_MAX_LINE_LEN,
        description="Maximum characters per line",
    )
    bash_timeout: int = Field(
        default=DEFAULT_BASH_TIMEOUT,
        description="Default timeout for bash commands in seconds",
    )
    grep_cap: int = Field(
        default=DEFAULT_GREP_CAP,
        description="Maximum number of grep matches before truncation",
    )
    yolo: bool = Field(
        default=False,
        description="Bypass dangerous command confirmations",
    )

    # Class variable for singleton instance
    _instance: ClassVar[Settings | None] = None

    def __init__(self, **data) -> None:
        """
        Initialize settings, loading from .env and environment variables.

        This allows Settings() to use defaults while supporting env vars.
        """
        # Load .env file first
        load_dotenv()

        # Apply environment variable overrides for defaults
        env_base_url = os.environ.get("BASE_URL", "")
        if env_base_url and "base_url" not in data:
            data["base_url"] = env_base_url.rstrip("/")

        env_api_key = os.environ.get("API_KEY", "")
        if env_api_key and "api_key" not in data:
            data["api_key"] = env_api_key

        env_model = os.environ.get("MODEL_NAME", "")
        if env_model and "model_name" not in data:
            data["model_name"] = env_model

        env_yolo = os.environ.get("NANOCODE_YOLO", "").lower()
        if env_yolo in ("1", "true", "yes") and "yolo" not in data:
            data["yolo"] = True

        super().__init__(**data)

    @classmethod
    def get_instance(cls) -> Settings:
        """
        Get the singleton instance of Settings.

        Creates the instance if it doesn't exist.

        Returns:
            The singleton Settings instance.
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """
        Reset the singleton instance.

        Useful for testing or when configuration changes dynamically.
        """
        cls._instance = None


def get_settings() -> Settings:
    """
    Get the current settings instance.

    This is a convenience function that returns the singleton Settings.

    Returns:
        The current Settings instance.
    """
    return Settings.get_instance()
