"""Global tool registry.

Tools register themselves via the ``@register_tool`` decorator at
import time; the CLI imports ``nanocode.tools`` once at startup, which
triggers registration of every built-in tool.
"""

from __future__ import annotations

from typing import Any

from nanocode.tools.base import BaseTool

_registry: dict[str, BaseTool] = {}


def register_tool(tool_class: type[BaseTool]) -> type[BaseTool]:
    """Class decorator: instantiate the tool and register it by name."""
    instance = tool_class()
    _registry[instance.name] = instance
    return tool_class


def get_tool(name: str) -> BaseTool | None:
    return _registry.get(name)


def list_tools() -> dict[str, dict[str, Any]]:
    """Return ``{name: {description, parameters}}`` for every registered tool."""
    return {
        name: {"description": tool.description, "parameters": tool.parameters}
        for name, tool in _registry.items()
    }


def get_schema() -> list[dict[str, Any]]:
    """Build the OpenAI function-calling schema for every registered tool."""
    schema = []
    for name, tool in _registry.items():
        properties: dict[str, dict[str, str]] = {}
        required: list[str] = []
        for param_name, param_type in tool.parameters.items():
            optional = param_type.endswith("?")
            properties[param_name] = {"type": param_type.rstrip("?")}
            if not optional:
                required.append(param_name)
        schema.append({
            "type": "function",
            "function": {
                "name": name,
                "description": tool.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            },
        })
    return schema


def run_tool(name: str, args: dict[str, Any]) -> str:
    """Execute a registered tool. Unknown names and exceptions become error strings."""
    tool = _registry.get(name)
    if tool is None:
        return f"error: unknown tool {name!r}"
    try:
        return tool.execute(args)
    except Exception as err:
        return f"error: {type(err).__name__}: {err}"
