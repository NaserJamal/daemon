"""
Sub-agent spawning tool for nanocode.

Spawns a recursive instance of the AI with the same tools for
open-ended research tasks. The AI only sees the final summary,
not the intermediate steps.

Example:
    >>> from nanocode.tools.explore import ExploreTool
    >>> tool = ExploreTool()
    >>> result = tool.execute({"prompt": "Investigate how X handles Y"})
"""

from __future__ import annotations

import json
from typing import Any, ClassVar

from nanocode.tools.base import BaseTool
from nanocode.tools.registry import register_tool


@register_tool
class ExploreTool(BaseTool):
    """
    Tool for spawning recursive AI agents.

    Creates a sub-agent with the same tools and capabilities to
    investigate topics or perform research tasks. The parent agent
    only receives the final summary, not the intermediate steps,
    keeping context clean.

    This is useful for open-ended research like "find where X is
    handled" or "summarize module Y" without cluttering the main
    conversation.

    Attributes:
        name: Always "explore".
        description: Human-readable description for the AI.
        parameters: Parameter schema with prompt.

    Example:
        >>> tool = ExploreTool()
        >>> result = tool.execute({
        ...     "prompt": "Find all usages of function X in the codebase"
        ... })
        >>> print(result)
        'Found in: main.py:45, utils.py:123, tests.py:67'
    """

    name = "explore"
    description = (
        "Spawn a sub-agent with the same tools to investigate something. "
        "You only see its final summary - tool calls and intermediate steps "
        "are hidden. Use for open-ended research ('find where X is handled', "
        "'summarize module Y') to keep your own context clean."
    )
    parameters = {
        "prompt": "string",
    }

    def execute(self, args: dict[str, Any]) -> str:
        """
        Spawn a sub-agent to investigate a topic.

        Args:
            args: Dictionary containing:
                - prompt: The research question or investigation task.

        Returns:
            The sub-agent's final response/summary.
        """
        # Import here to avoid circular imports at module load time
        from nanocode.core.api import call_api
        from nanocode.core.prompt import get_default_system_prompt
        from nanocode.tools.registry import run_tool, get_schema

        prompt = args["prompt"]

        # Build initial messages for sub-agent
        sub = [
            {"role": "system", "content": get_default_system_prompt()},
            {"role": "user", "content": prompt},
        ]

        # Get schema for tool calling
        schema = get_schema()

        # Main loop for sub-agent
        while True:
            # Call API
            response = call_api(sub, tools=schema)
            message = response["choices"][0]["message"]

            content = message.get("content") or ""
            tool_calls = message.get("tool_calls") or []

            # Build assistant message with reasoning if present
            assistant_msg: dict[str, Any] = {"role": "assistant", "content": content}

            # Providers disagree on the field name for reasoning
            for key in ("reasoning_content", "reasoning", "reasoning_details"):
                if message.get(key) is not None:
                    assistant_msg[key] = message[key]

            if tool_calls:
                assistant_msg["tool_calls"] = tool_calls

            sub.append(assistant_msg)

            # If no tool calls, return the content
            if not tool_calls:
                return content or "(no response)"

            # Execute tool calls
            for call in tool_calls:
                try:
                    tool_args = json.loads(call["function"].get("arguments") or "{}")
                except json.JSONDecodeError:
                    tool_args = {}

                result = run_tool(call["function"]["name"], tool_args)

                sub.append({
                    "role": "tool",
                    "tool_call_id": call.get("id", ""),
                    "content": result,
                })
