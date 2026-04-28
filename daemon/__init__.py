"""daemon - minimal agentic coding harness for any OpenAI-compatible endpoint."""

from daemon.core.api import call_api
from daemon.core.config import Settings, get_settings
from daemon.tools import (
    BaseTool,
    get_schema,
    get_tool,
    list_tools,
    register_tool,
    run_tool,
)

__version__ = "0.1.0"

__all__ = [
    "BaseTool",
    "Settings",
    "__version__",
    "call_api",
    "get_schema",
    "get_settings",
    "get_tool",
    "list_tools",
    "register_tool",
    "run_tool",
]
