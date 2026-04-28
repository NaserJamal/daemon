"""
Tool registry for nanocode.

Provides the central registry for all tools. Tools register themselves
using the @register_tool decorator.

Example:
    >>> from nanocode.tools.registry import register_tool, get_tool, list_tools
    >>> @register_tool
    ... class MyTool(BaseTool):
    ...     name = "my_tool"
    ...     ...
"""

from __future__ import annotations

from typing import Any

# Module-level registry: name -> (tool_instance, description, parameters)
_registry: dict[str, tuple[Any, str, dict[str, str]]] = {}


def register_tool(tool_class: type) -> type:
    """
    Decorator to register a tool with the global registry.

    The tool class must have class attributes: name, description, parameters.

    Args:
        tool_class: The tool class to register.

    Returns:
        The same class (for use as a decorator).

    Example:
        >>> @register_tool
        ... class MyTool(BaseTool):
        ...     name = "my_tool"
        ...     description = "Does something useful"
        ...     parameters = {"arg": "string"}
        ...     def execute(self, args):
        ...         return "result"
    """
    tool_instance = tool_class()
    name = tool_instance.name
    description = tool_instance.description
    parameters = tool_instance.parameters

    _registry[name] = (tool_instance, description, parameters)
    return tool_class


def unregister_tool(name: str) -> bool:
    """
    Remove a tool from the registry.

    Args:
        name: The name of the tool to remove.

    Returns:
        True if the tool was removed, False if it wasn't registered.
    """
    if name in _registry:
        del _registry[name]
        return True
    return False


def get_tool(name: str) -> Any | None:
    """
    Get a registered tool by name.

    Args:
        name: The name of the tool.

    Returns:
        The tool instance, or None if not found.
    """
    entry = _registry.get(name)
    if entry:
        return entry[0]
    return None


def list_tools() -> dict[str, dict[str, Any]]:
    """
    List all registered tools.

    Returns:
        Dictionary mapping tool names to their info dictionaries.
    """
    result = {}
    for name, (_, description, parameters) in _registry.items():
        result[name] = {
            "description": description,
            "parameters": parameters,
        }
    return result


def get_schema() -> list[dict[str, Any]]:
    """
    Generate the OpenAI function-calling schema for all tools.

    Returns:
        List of tool schema dictionaries for API calls.
    """
    schema = []
    for name, (_, description, params) in _registry.items():
        properties: dict[str, dict[str, str]] = {}
        required: list[str] = []

        for param_name, param_type in params.items():
            optional = param_type.endswith("?")
            clean_type = param_type.rstrip("?")
            properties[param_name] = {"type": clean_type}
            if not optional:
                required.append(param_name)

        schema.append({
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            },
        })

    return schema


def run_tool(name: str, args: dict[str, Any]) -> str:
    """
    Execute a registered tool with the given arguments.

    Args:
        name: The name of the tool to execute.
        args: Dictionary of arguments to pass to the tool.

    Returns:
        The tool's output string, or an error message.

    Example:
        >>> result = run_tool("read", {"path": "file.txt"})
        >>> print(result)
    """
    tool = get_tool(name)
    if tool is None:
        return f"error: unknown tool {name!r}"

    try:
        return tool.execute(args)
    except Exception as err:
        return f"error: {type(err).__name__}: {err}"


def clear_registry() -> None:
    """
    Clear all registered tools.

    Useful for testing or resetting the tool set.
    """
    _registry.clear()


def get_registry() -> dict[str, tuple[Any, str, dict[str, str]]]:
    """
    Get the raw registry dictionary.

    Returns:
        The internal registry dictionary.
    """
    return _registry.copy()
