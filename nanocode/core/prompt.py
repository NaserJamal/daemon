"""
System prompt management for nanocode.

Handles generation of system prompts, including dynamic injection
of tool descriptions and context information.

Example:
    >>> from nanocode.core.prompt import PromptManager, get_default_system_prompt
    >>> prompt = get_default_system_prompt()
    >>> print("cwd:" in prompt)
    True
"""

from __future__ import annotations

import os
from typing import Any

from nanocode.tools import list_tools


def get_default_system_prompt() -> str:
    """
    Get the default system prompt with current working directory.

    Returns:
        The default system prompt string.
    """
    return f"You are a concise coding assistant operating in a terminal.\ncwd: {os.getcwd()}"


class PromptManager:
    """
    Manages system prompts with dynamic content injection.

    This class handles the generation of system prompts, including
    adding tool descriptions, context information, and dynamic content.

    Attributes:
        base_prompt: The base system prompt.
        tool_descriptions: Whether to include tool descriptions.

    Example:
        >>> manager = PromptManager()
        >>> manager.include_tool_descriptions()
        >>> prompt = manager.build()
    """

    def __init__(
        self,
        base_prompt: str | None = None,
        include_tool_descriptions: bool = True,
    ) -> None:
        """
        Initialize the prompt manager.

        Args:
            base_prompt: Optional base prompt. Uses default if None.
            include_tool_descriptions: Whether to include tool descriptions.
        """
        self.base_prompt = base_prompt or get_default_system_prompt()
        self.include_tool_descriptions = include_tool_descriptions
        self._custom_sections: list[str] = []

    def add_section(self, content: str) -> PromptManager:
        """
        Add a custom section to the prompt.

        Args:
            content: The section content to add.

        Returns:
            Self for method chaining.
        """
        self._custom_sections.append(content)
        return self

    def set_base(self, prompt: str) -> PromptManager:
        """
        Set a new base prompt.

        Args:
            prompt: The new base prompt.

        Returns:
            Self for method chaining.
        """
        self.base_prompt = prompt
        return self

    def with_cwd(self, cwd: str | None = None) -> PromptManager:
        """
        Update the prompt with current working directory.

        Args:
            cwd: The current working directory. Uses os.getcwd() if None.

        Returns:
            Self for method chaining.
        """
        if cwd is None:
            cwd = os.getcwd()
        # Append or update cwd in prompt
        if "cwd:" in self.base_prompt:
            self.base_prompt = self.base_prompt.split("cwd:")[0] + f"cwd: {cwd}"
        else:
            self.base_prompt += f"\ncwd: {cwd}"
        return self

    def include_tool_descriptions(self) -> PromptManager:
        """
        Enable tool descriptions in the prompt.

        Returns:
            Self for method chaining.
        """
        self.include_tool_descriptions = True
        return self

    def exclude_tool_descriptions(self) -> PromptManager:
        """
        Disable tool descriptions in the prompt.

        Returns:
            Self for method chaining.
        """
        self.include_tool_descriptions = False
        return self

    def build(self) -> str:
        """
        Build the final system prompt.

        Returns:
            The complete system prompt string.
        """
        parts = [self.base_prompt]

        if self.include_tool_descriptions:
            tools = list_tools()
            if tools:
                tool_section = "\n\nAvailable tools:"
                for tool_name, tool_info in tools.items():
                    desc = tool_info.get("description", "No description")
                    params = tool_info.get("parameters", {})
                    param_str = ", ".join(
                        f"{k}{'' if v.endswith('?') else ' (required)'}"
                        for k, v in params.items()
                    )
                    tool_section += f"\n- {tool_name}({param_str}): {desc}"
                parts.append(tool_section)

        for section in self._custom_sections:
            parts.append(section)

        return "\n".join(parts)

    def to_dict(self, role: str = "system") -> dict[str, Any]:
        """
        Convert the prompt to a message dictionary.

        Args:
            role: The message role. Defaults to "system".

        Returns:
            Dictionary with role and content.
        """
        return {"role": role, "content": self.build()}
