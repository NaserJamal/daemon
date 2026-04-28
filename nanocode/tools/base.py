"""
Base class for nanocode tools.

Tools extend the AI's capabilities through function calling.
Each tool implements a specific capability (file reading, bash, etc.)
and provides its own schema for the API.

Example:
    >>> from nanocode.tools.base import BaseTool
    >>> class MyTool(BaseTool):
    ...     name = "my_tool"
    ...     description = "Does something useful"
    ...     parameters = {"input": "string", "count": "integer?"}
    ...     def execute(self, args):
    ...         return f"Processed: {args['input']}"
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, ClassVar

from pydantic import BaseModel, Field


class ToolSchema(BaseModel):
    """
    Schema definition for a tool's parameters.

    Attributes:
        name: The parameter name.
        type: The parameter type (string, integer, boolean, etc.).
        description: Human-readable description of the parameter.
        required: Whether this parameter is required.
    """

    name: str
    type: str
    description: str = ""
    required: bool = True


class BaseTool(ABC):
    """
    Abstract base class for all nanocode tools.

    Tools provide capabilities to the AI through function calling.
    Each tool must define its name, description, parameters, and
    implement the execute method.

    Attributes:
        name: The tool's unique identifier.
        description: Human-readable description for the AI.
        parameters: Dictionary mapping parameter names to types.
                   Types ending with '?' are optional.

    Type Annotations (ClassVar):
        These should be overridden by subclasses.

    Example:
        >>> class ReadTool(BaseTool):
        ...     name = "read"
        ...     description = "Read a file"
        ...     parameters = {"path": "string"}
        ...
        ...     def execute(self, args):
        ...         with open(args["path"]) as f:
        ...             return f.read()
    """

    # Class variables - should be overridden by subclasses
    name: ClassVar[str] = ""
    description: ClassVar[str] = ""
    parameters: ClassVar[dict[str, str]] = {}

    @abstractmethod
    def execute(self, args: dict[str, Any]) -> str:
        """
        Execute the tool with the given arguments.

        Args:
            args: Dictionary of arguments from the AI call.

        Returns:
            A string result to send back to the AI.

        Note:
            Subclasses must implement this method.
            Errors should be caught and returned as error strings.
        """
        ...

    def get_schema(self) -> dict[str, Any]:
        """
        Get the JSON schema for this tool's parameters.

        Returns:
            Dictionary suitable for OpenAI function calling schema.
        """
        properties: dict[str, dict[str, str]] = {}
        required: list[str] = []

        for param_name, param_type in self.parameters.items():
            optional = param_type.endswith("?")
            clean_type = param_type.rstrip("?")
            properties[param_name] = {"type": clean_type}
            if not optional:
                required.append(param_name)

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            },
        }

    def validate_args(self, args: dict[str, Any]) -> tuple[bool, str]:
        """
        Validate arguments against the tool's parameter schema.

        Args:
            args: The arguments to validate.

        Returns:
            Tuple of (is_valid, error_message).
        """
        for param_name, param_type in self.parameters.items():
            # Skip optional parameters
            if param_type.endswith("?"):
                continue

            # Check required parameters exist
            if param_name not in args:
                return False, f"Missing required parameter: {param_name}"

            # Type checking
            expected_type = param_type.rstrip("?")
            arg_value = args[param_name]

            if expected_type == "string":
                if not isinstance(arg_value, str):
                    return False, f"Parameter {param_name} must be a string"
            elif expected_type == "integer":
                if not isinstance(arg_value, int) or isinstance(arg_value, bool):
                    return False, f"Parameter {param_name} must be an integer"
            elif expected_type == "boolean":
                if not isinstance(arg_value, bool):
                    return False, f"Parameter {param_name} must be a boolean"

        return True, ""

    def __repr__(self) -> str:
        """Return a string representation of the tool."""
        return f"{self.__class__.__name__}(name={self.name!r})"
