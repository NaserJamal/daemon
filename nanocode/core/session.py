"""
Message session management for nanocode.

The Session class manages conversation history, including system prompts,
user messages, assistant responses, and tool call interactions.

Example:
    >>> from nanocode.core.session import Session
    >>> session = Session()
    >>> session.add_user("Hello, how are you?")
    >>> print(len(session.messages))
    2
"""

from __future__ import annotations

import json
from typing import Any, Literal

from nanocode.core.prompt import get_default_system_prompt


MessageRole = Literal["system", "user", "assistant", "tool"]


class Session:
    """
    Manages a conversation session with message history.

    The session maintains a list of messages in order, with support for
    system prompts, user messages, assistant responses, and tool calls.
    This class handles the complexity of tracking multi-turn conversations
    with interleaved reasoning and function calling.

    Attributes:
        messages: List of message dictionaries in chronological order.

    Example:
        >>> session = Session()
        >>> session.add_user("Write a hello world program")
        >>> session.add_assistant("Sure! Here's a Python program:")
        >>> print(session.messages[-1]["content"])
        "Sure! Here's a Python program:"
    """

    def __init__(
        self,
        system_prompt: str | None = None,
        initial_messages: list[dict[str, Any]] | None = None,
    ) -> None:
        """
        Initialize a new session.

        Args:
            system_prompt: Optional custom system prompt. Uses default if None.
            initial_messages: Optional list of messages to start with.
        """
        if system_prompt is None:
            system_prompt = get_default_system_prompt()

        if initial_messages is not None:
            self.messages: list[dict[str, Any]] = list(initial_messages)
        else:
            self.messages = [{"role": "system", "content": system_prompt}]

    def add_user(self, content: str) -> None:
        """
        Add a user message to the session.

        Args:
            content: The user's message content.
        """
        self.messages.append({"role": "user", "content": content})

    def add_assistant(
        self,
        content: str,
        tool_calls: list[dict[str, Any]] | None = None,
        reasoning: str | None = None,
    ) -> None:
        """
        Add an assistant message to the session.

        Args:
            content: The assistant's message content.
            tool_calls: Optional list of tool calls made by the assistant.
            reasoning: Optional reasoning content (for models that support it).
        """
        message: dict[str, Any] = {"role": "assistant", "content": content}

        # Add reasoning if present (models may use different field names)
        if reasoning is not None:
            message["reasoning_content"] = reasoning

        if tool_calls:
            message["tool_calls"] = tool_calls

        self.messages.append(message)

    def add_tool(
        self,
        content: str,
        tool_call_id: str = "",
        name: str | None = None,
    ) -> None:
        """
        Add a tool response message to the session.

        Args:
            content: The tool's response content.
            tool_call_id: The ID of the tool call this responds to.
            name: Optional name of the tool (for tracking).
        """
        message: dict[str, Any] = {
            "role": "tool",
            "content": content,
        }

        if tool_call_id:
            message["tool_call_id"] = tool_call_id

        if name:
            message["name"] = name

        self.messages.append(message)

    def clear(self) -> None:
        """
        Clear all messages except the system prompt.

        Resets the session to its initial state with only the system prompt.
        """
        system_message = self.messages[0] if self.messages else None
        self.messages = []
        if system_message is None:
            self.messages.append({"role": "system", "content": get_default_system_prompt()})
        elif system_message.get("role") == "system":
            self.messages.append(system_message)

    def get_messages(self) -> list[dict[str, Any]]:
        """
        Get all messages in the session.

        Returns:
            A copy of the message list.
        """
        return list(self.messages)

    def get_last_user_message(self) -> str | None:
        """
        Get the content of the most recent user message.

        Returns:
            The user's message content, or None if no user messages exist.
        """
        for message in reversed(self.messages):
            if message.get("role") == "user":
                return message.get("content")
        return None

    def serialize(self) -> str:
        """
        Serialize the session to a JSON string.

        Useful for debugging or persisting conversation history.

        Returns:
            JSON string representation of the session.
        """
        return json.dumps(self.messages, indent=2)

    def deserialize(self, data: str) -> None:
        """
        Load a session from a JSON string.

        Args:
            data: JSON string containing message history.
        """
        self.messages = json.loads(data)

    def __len__(self) -> int:
        """Return the number of messages in the session."""
        return len(self.messages)

    def __repr__(self) -> str:
        """Return a string representation of the session."""
        return f"Session(messages={len(self.messages)})"
