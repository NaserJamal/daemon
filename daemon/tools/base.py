"""Abstract base class for tools.

A tool exposes a callable to the LLM via OpenAI's function-calling
schema. Each subclass declares ``name``, ``description``, and a
``parameters`` mapping (parameter name -> JSON Schema type, with a
trailing ``?`` to mark optional). The runtime schema is generated
from those class attributes by the registry.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, ClassVar


class BaseTool(ABC):
    """Subclass and decorate with ``@register_tool`` to make a tool available."""

    name: ClassVar[str] = ""
    description: ClassVar[str] = ""
    # Each value is a JSON Schema type; suffix "?" denotes an optional parameter.
    parameters: ClassVar[dict[str, str]] = {}

    @abstractmethod
    def execute(self, args: dict[str, Any]) -> str:
        """Run the tool. Return a string for the model. Errors are caught upstream."""
        ...
