"""
nanocode - Minimal agentic coding harness for any OpenAI-compatible endpoint.

This package provides a modular, extensible CLI for AI-assisted coding tasks.
It supports various tools for file operations, code search, and shell execution
with built-in safety features.

Example:
    >>> import nanocode
    >>> from nanocode.core.config import Settings
    >>> settings = Settings()
    >>> print(settings.model_name)
    'gpt-4o-mini'
"""

__version__ = "0.1.0"
__author__ = "Nanocode Contributors"

# Core exports
from nanocode.core.config import Settings, load_dotenv
from nanocode.core.api import call_api
from nanocode.core.session import Session
from nanocode.tools import (
    register_tool,
    get_tool,
    list_tools,
    get_schema,
    run_tool,
    clear_registry,
)

__all__ = [
    "__version__",
    "Settings",
    "load_dotenv",
    "call_api",
    "Session",
    "register_tool",
    "get_tool",
    "list_tools",
    "get_schema",
    "run_tool",
    "clear_registry",
]
