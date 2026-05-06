"""HTTP client for OpenAI-compatible chat completions."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Callable, Iterable
from typing import Any

from daemon.core import debug
from daemon.core.config import Settings, get_settings


def call_api(
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None = None,
    settings: Settings | None = None,
    *,
    stream: bool = False,
    on_content_delta: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    """POST a chat-completion request and return the parsed JSON response.

    Args:
        messages: Conversation messages in OpenAI format.
        tools: Tool schemas. Auto-generated from the registry if omitted.
        settings: Override the global Settings (mostly useful for tests).
        stream: If True, request server-sent events and assemble the final
            response from incremental deltas. The return shape matches the
            non-streaming response.
        on_content_delta: Called with each content text delta when streaming.

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
    if stream:
        body["stream"] = True
        # Without this OpenAI omits the final usage chunk in stream mode.
        body["stream_options"] = {"include_usage": True}

    url = f"{settings.base_url}/chat/completions"
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.api_key}",
        },
    )
    debug.log_event("request", {"url": url, "body": body})
    try:
        with urllib.request.urlopen(request) as response:
            payload: dict[str, Any]
            if stream:
                payload = _accumulate_stream(response, on_content_delta)
            else:
                payload = json.loads(response.read())
            debug.log_event("response", payload)
            return payload
    except urllib.error.HTTPError as err:
        body_text = err.read().decode("utf-8", errors="replace")
        debug.log_event("http_error", {"code": err.code, "body": body_text})
        raise RuntimeError(f"HTTP {err.code}: {body_text}") from None


def _accumulate_stream(
    response: Iterable[bytes],
    on_content_delta: Callable[[str], None] | None,
) -> dict[str, Any]:
    """Read SSE chunks and assemble a non-streaming-shaped response dict.

    The OpenAI streaming protocol emits ``data: {json}\\n\\n`` events plus a
    terminating ``data: [DONE]``. Tool-call argument fragments are joined by
    index since they cannot be acted on until the call is complete.
    """
    message: dict[str, Any] = {"role": "assistant", "content": ""}
    tool_calls: dict[int, dict[str, Any]] = {}
    usage: dict[str, Any] | None = None

    for raw in response:
        line = raw.decode("utf-8", errors="replace").strip()
        if not line.startswith("data:"):
            continue
        data = line[5:].strip()
        if data == "[DONE]":
            break
        try:
            chunk = json.loads(data)
        except json.JSONDecodeError:
            continue

        chunk_usage = chunk.get("usage")
        if isinstance(chunk_usage, dict):
            usage = chunk_usage

        for choice in chunk.get("choices") or []:
            delta = choice.get("delta") or {}
            if "role" in delta:
                message["role"] = delta["role"]

            content = delta.get("content")
            if isinstance(content, str) and content:
                message["content"] += content
                if on_content_delta is not None:
                    on_content_delta(content)

            # reasoning_content streams as concatenable string deltas; the
            # other reasoning fields are passed through whole, since providers
            # disagree on their shape.
            r_content = delta.get("reasoning_content")
            if isinstance(r_content, str) and r_content:
                message["reasoning_content"] = (message.get("reasoning_content") or "") + r_content
            for key in ("reasoning", "reasoning_details"):
                if delta.get(key) is not None:
                    message[key] = delta[key]

            for tc in delta.get("tool_calls") or []:
                idx = tc.get("index", 0)
                slot = tool_calls.setdefault(
                    idx,
                    {"id": "", "type": "function", "function": {"name": "", "arguments": ""}},
                )
                if tc.get("id"):
                    slot["id"] = tc["id"]
                if tc.get("type"):
                    slot["type"] = tc["type"]
                fn = tc.get("function") or {}
                if fn.get("name"):
                    slot["function"]["name"] = fn["name"]
                if fn.get("arguments"):
                    slot["function"]["arguments"] += fn["arguments"]

    if tool_calls:
        message["tool_calls"] = [tool_calls[i] for i in sorted(tool_calls)]

    result: dict[str, Any] = {"choices": [{"message": message}]}
    if usage is not None:
        result["usage"] = usage
    return result
