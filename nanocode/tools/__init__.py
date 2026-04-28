"""
Tools module for nanocode.

Provides a plugin architecture for tool registration and execution.
Tools extend the AI's capabilities for file operations, code search,
shell execution, and more.

Example:
    >>> from nanocode.tools.registry import register_tool, get_tool, list_tools
    >>> @register_tool
    ... class MyTool(BaseTool):
    ...     name = "my_tool"
    ...     ...
"""

from __future__ import annotations

from typing import Any

# Re-export from registry for convenience
from nanocode.tools.registry import (
    register_tool,
    unregister_tool,
    get_tool,
    list_tools,
    get_schema,
    run_tool,
    clear_registry,
    get_registry,
)

# Import base class
from nanocode.tools.base import BaseTool, ToolSchema

# Import tools to trigger registration via decorator
# These must come after the registry is defined
from nanocode.tools.read import ReadTool
from nanocode.tools.write import WriteTool
from nanocode.tools.edit import EditTool
from nanocode.tools.glob import GlobTool
from nanocode.tools.grep import GrepTool
from nanocode.tools.bash import BashTool
from nanocode.tools.explore import ExploreTool


__all__ = [
    "BaseTool",
    "ToolSchema",
    "register_tool",
    "unregister_tool",
    "get_tool",
    "list_tools",
    "get_schema",
    "run_tool",
    "clear_registry",
    "get_registry",
]
