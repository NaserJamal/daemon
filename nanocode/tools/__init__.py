"""Tool registry plus auto-registration of every built-in tool.

Importing this package eagerly imports the tool modules below, each of
which calls ``@register_tool`` at module load to populate the registry.
"""

from nanocode.tools.base import BaseTool
from nanocode.tools.registry import (
    get_schema,
    get_tool,
    list_tools,
    register_tool,
    run_tool,
)

# Side-effect imports: each module registers its tool on import.
from nanocode.tools import bash, edit, explore, glob, grep, read, write  # noqa: F401

__all__ = [
    "BaseTool",
    "get_schema",
    "get_tool",
    "list_tools",
    "register_tool",
    "run_tool",
]
