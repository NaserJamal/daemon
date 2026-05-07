"""Tool registry plus auto-registration of every built-in tool.

Importing this package eagerly imports the tool modules below, each of
which calls ``@register_tool`` at module load to populate the registry.
"""

# Side-effect imports: each module registers its tool on import.
from daemon.tools import bash, edit, fetch, glob, grep, read, task, write  # noqa: F401
from daemon.tools.base import BaseTool
from daemon.tools.registry import (
    get_schema,
    get_tool,
    list_tools,
    register_tool,
    run_tool,
)

__all__ = [
    "BaseTool",
    "get_schema",
    "get_tool",
    "list_tools",
    "register_tool",
    "run_tool",
]
