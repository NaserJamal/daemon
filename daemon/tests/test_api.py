"""Tests for the chat-completions client, including streaming assembly."""

from __future__ import annotations

import json
from collections.abc import Iterable, Iterator
from typing import Any
from unittest.mock import patch

from daemon.core import api
from daemon.core.config import Settings


class _MockResponse:
    """Stand-in for ``urlopen`` that yields pre-canned bytes lines."""

    def __init__(self, lines: Iterable[bytes] | bytes):
        if isinstance(lines, bytes):
            self._payload = lines
            self._lines: list[bytes] = []
        else:
            self._payload = b""
            self._lines = list(lines)

    def __enter__(self) -> _MockResponse:
        return self

    def __exit__(self, *_: Any) -> None:
        return None

    def __iter__(self) -> Iterator[bytes]:
        return iter(self._lines)

    def read(self) -> bytes:
        return self._payload


def _sse(events: list[dict[str, Any]]) -> list[bytes]:
    """Encode events as SSE lines, terminated by ``data: [DONE]``."""
    out = [f"data: {json.dumps(e)}\n".encode() for e in events]
    out.append(b"data: [DONE]\n")
    return out


def _settings() -> Settings:
    return Settings(api_key="x", base_url="https://example.test", model_name="m")


class TestNonStreaming:
    def test_returns_parsed_json(self) -> None:
        body = {"choices": [{"message": {"role": "assistant", "content": "hi"}}]}
        with patch(
            "daemon.core.api.urllib.request.urlopen",
            return_value=_MockResponse(json.dumps(body).encode()),
        ):
            result = api.call_api(
                [{"role": "user", "content": "hi"}], tools=[], settings=_settings()
            )
        assert result == body


class TestStreaming:
    def test_assembles_content_deltas(self) -> None:
        events: list[dict[str, Any]] = [
            {"choices": [{"delta": {"role": "assistant", "content": "Hel"}}]},
            {"choices": [{"delta": {"content": "lo"}}]},
            {"choices": [{"delta": {"content": " world"}, "finish_reason": "stop"}]},
        ]
        seen: list[str] = []
        with patch(
            "daemon.core.api.urllib.request.urlopen", return_value=_MockResponse(_sse(events))
        ):
            result = api.call_api(
                [{"role": "user", "content": "hi"}],
                tools=[],
                settings=_settings(),
                stream=True,
                on_content_delta=seen.append,
            )
        assert result["choices"][0]["message"]["content"] == "Hello world"
        assert result["choices"][0]["message"]["role"] == "assistant"
        assert seen == ["Hel", "lo", " world"]

    def test_assembles_tool_calls_across_chunks(self) -> None:
        events: list[dict[str, Any]] = [
            {
                "choices": [
                    {
                        "delta": {
                            "role": "assistant",
                            "tool_calls": [
                                {
                                    "index": 0,
                                    "id": "call_1",
                                    "type": "function",
                                    "function": {"name": "bash", "arguments": '{"co'},
                                }
                            ],
                        }
                    }
                ]
            },
            {
                "choices": [
                    {
                        "delta": {
                            "tool_calls": [{"index": 0, "function": {"arguments": 'mmand":"ls"}'}}]
                        }
                    }
                ]
            },
            {"choices": [{"delta": {}, "finish_reason": "tool_calls"}]},
        ]
        with patch(
            "daemon.core.api.urllib.request.urlopen", return_value=_MockResponse(_sse(events))
        ):
            result = api.call_api([], tools=[], settings=_settings(), stream=True)
        message = result["choices"][0]["message"]
        assert message.get("content") == ""
        calls = message["tool_calls"]
        assert len(calls) == 1
        assert calls[0]["id"] == "call_1"
        assert calls[0]["type"] == "function"
        assert calls[0]["function"]["name"] == "bash"
        assert json.loads(calls[0]["function"]["arguments"]) == {"command": "ls"}

    def test_multiple_tool_calls_indexed(self) -> None:
        events: list[dict[str, Any]] = [
            {
                "choices": [
                    {
                        "delta": {
                            "tool_calls": [
                                {
                                    "index": 0,
                                    "id": "a",
                                    "function": {"name": "read", "arguments": "{}"},
                                },
                                {
                                    "index": 1,
                                    "id": "b",
                                    "function": {"name": "bash", "arguments": "{}"},
                                },
                            ]
                        }
                    }
                ]
            },
        ]
        with patch(
            "daemon.core.api.urllib.request.urlopen", return_value=_MockResponse(_sse(events))
        ):
            result = api.call_api([], tools=[], settings=_settings(), stream=True)
        calls = result["choices"][0]["message"]["tool_calls"]
        assert [c["id"] for c in calls] == ["a", "b"]
        assert [c["function"]["name"] for c in calls] == ["read", "bash"]

    def test_usage_block_captured(self) -> None:
        events: list[dict[str, Any]] = [
            {"choices": [{"delta": {"content": "x"}}]},
            {"choices": [], "usage": {"prompt_tokens": 12, "completion_tokens": 3}},
        ]
        with patch(
            "daemon.core.api.urllib.request.urlopen", return_value=_MockResponse(_sse(events))
        ):
            result = api.call_api([], tools=[], settings=_settings(), stream=True)
        assert result["usage"] == {"prompt_tokens": 12, "completion_tokens": 3}

    def test_reasoning_content_concatenates(self) -> None:
        events: list[dict[str, Any]] = [
            {"choices": [{"delta": {"reasoning_content": "thinking "}}]},
            {"choices": [{"delta": {"reasoning_content": "more"}}]},
            {"choices": [{"delta": {"content": "ok"}}]},
        ]
        with patch(
            "daemon.core.api.urllib.request.urlopen", return_value=_MockResponse(_sse(events))
        ):
            result = api.call_api([], tools=[], settings=_settings(), stream=True)
        assert result["choices"][0]["message"]["reasoning_content"] == "thinking more"

    def test_skips_blank_and_malformed_lines(self) -> None:
        lines = [
            b"\n",
            b": comment line\n",
            b"data: not-json\n",
            b'data: {"choices":[{"delta":{"content":"a"}}]}\n',
            b"data: [DONE]\n",
        ]
        with patch("daemon.core.api.urllib.request.urlopen", return_value=_MockResponse(lines)):
            result = api.call_api([], tools=[], settings=_settings(), stream=True)
        assert result["choices"][0]["message"]["content"] == "a"

    def test_stream_flag_added_to_request(self) -> None:
        captured: dict[str, Any] = {}

        def fake_urlopen(req: Any) -> _MockResponse:
            captured["body"] = json.loads(req.data.decode())
            return _MockResponse(_sse([{"choices": [{"delta": {"content": "ok"}}]}]))

        with patch("daemon.core.api.urllib.request.urlopen", side_effect=fake_urlopen):
            api.call_api([], tools=[], settings=_settings(), stream=True)
        assert captured["body"]["stream"] is True
        assert captured["body"]["stream_options"] == {"include_usage": True}

    def test_non_stream_request_omits_stream_flag(self) -> None:
        captured: dict[str, Any] = {}

        def fake_urlopen(req: Any) -> _MockResponse:
            captured["body"] = json.loads(req.data.decode())
            return _MockResponse(b'{"choices":[{"message":{"role":"assistant","content":"ok"}}]}')

        with patch("daemon.core.api.urllib.request.urlopen", side_effect=fake_urlopen):
            api.call_api([], tools=[], settings=_settings())
        assert "stream" not in captured["body"]
        assert "stream_options" not in captured["body"]
