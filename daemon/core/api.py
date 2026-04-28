"""HTTP client for OpenAI-compatible chat completions."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from daemon.core.config import Settings, get_settings


def call_api(
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None = None,
    settings: Settings | None = None,
) -> dict[str, Any]:
    """POST a chat-completion request and return the parsed JSON response.

    Args:
        messages: Conversation messages in OpenAI format.
        tools: Tool schemas. Auto-generated from the registry if omitted.
        settings: Override the global Settings (mostly useful for tests).

    Raises:
        RuntimeError: If the server returns a non-2xx response.
    """
    if settings is None:
        settings = get_settings()
    if tools is None:
        from daemon.tools import get_schema  # local import: avoid cycle

        tools = get_schema()

    body: dict[str, Any] = {"model": settings.model_name, "messages": messages}
    if tools:
        body["tools"] = tools

    request = urllib.request.Request(
        f"{settings.base_url}/chat/completions",
        data=json.dumps(body).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.api_key}",
        },
    )
    try:
        with urllib.request.urlopen(request) as response:
            payload: dict[str, Any] = json.loads(response.read())
            return payload
    except urllib.error.HTTPError as err:
        body_text = err.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {err.code}: {body_text}") from None
