"""
API client for nanocode.

Handles communication with OpenAI-compatible endpoints using the
chat completions API. Supports function calling for tool use.

Example:
    >>> from nanocode.core.api import call_api
    >>> messages = [{"role": "user", "content": "Hello"}]
    >>> response = call_api(messages)
    >>> print(response["choices"][0]["message"]["content"])
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from nanocode.core.config import Settings, get_settings


def call_api(
    messages: list[dict[str, Any]],
    settings: Settings | None = None,
    tools: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    Call the chat completions API with the given messages.

    Args:
        messages: List of message dictionaries with 'role' and 'content'.
        settings: Optional Settings instance. Uses global settings if None.
        tools: Optional list of tool definitions. Auto-generates from
               registry if None.

    Returns:
        The API response as a dictionary parsed from JSON.

    Raises:
        RuntimeError: If the API returns an HTTP error.
    """
    if settings is None:
        settings = get_settings()

    if tools is None:
        # Lazy import to avoid circular imports
        from nanocode.tools import get_schema
        tools = get_schema()

    request_body: dict[str, Any] = {
        "model": settings.model_name,
        "messages": messages,
    }

    if tools:
        request_body["tools"] = tools

    request = urllib.request.Request(
        f"{settings.base_url}/chat/completions",
        data=json.dumps(request_body).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.api_key}",
        },
    )

    try:
        with urllib.request.urlopen(request) as response:
            return json.loads(response.read())
    except urllib.error.HTTPError as err:
        body = err.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {err.code}: {body}") from None


def call_api_with_retry(
    messages: list[dict[str, Any]],
    max_retries: int = 3,
    settings: Settings | None = None,
    tools: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    Call the API with automatic retry on transient failures.

    Args:
        messages: List of message dictionaries.
        max_retries: Maximum number of retry attempts.
        settings: Optional Settings instance.
        tools: Optional tool schema.

    Returns:
        The API response as a dictionary.

    Raises:
        RuntimeError: If all retry attempts fail.
    """
    last_error: Exception | None = None

    for attempt in range(max_retries):
        try:
            return call_api(messages, settings, tools)
        except (urllib.error.URLError, RuntimeError) as e:
            last_error = e
            if attempt < max_retries - 1:
                continue
            raise RuntimeError(
                f"API call failed after {max_retries} attempts: {last_error}"
            ) from last_error

    # Should not reach here, but satisfy type checker
    raise RuntimeError("Unexpected error in call_api_with_retry")
