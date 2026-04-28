"""Tests for the slash-command registry and built-in handlers."""

from __future__ import annotations

from typing import Any

import pytest
from daemon.cli import commands


@pytest.fixture
def messages() -> list[dict[str, Any]]:
    """Fresh message list with a placeholder system prompt and one user turn."""
    return [
        {"role": "system", "content": "old system prompt"},
        {"role": "user", "content": "hello"},
    ]


class TestRegistry:
    def test_registers_builtins(self) -> None:
        names = {c.name for c in commands.commands()}
        assert {"/help", "/clear", "/config", "/quit"} <= names

    def test_aliases_dispatch_to_same_command(self) -> None:
        # `/q`, `/exit`, and `exit` should all be wired to /quit.
        assert commands.handle("/q", []) is False
        assert commands.handle("/exit", []) is False
        assert commands.handle("exit", []) is False


class TestHelp:
    def test_help_lists_all_commands(
        self, messages: list[dict[str, Any]], capsys: pytest.CaptureFixture[str]
    ) -> None:
        result = commands.handle("/help", messages)
        out = capsys.readouterr().out
        assert result is True
        for cmd in commands.commands():
            assert cmd.name in out
            assert cmd.description in out

    def test_help_alias(
        self, messages: list[dict[str, Any]], capsys: pytest.CaptureFixture[str]
    ) -> None:
        assert commands.handle("/?", messages) is True
        assert "/help" in capsys.readouterr().out


class TestClear:
    def test_clear_resets_messages(self, messages: list[dict[str, Any]]) -> None:
        result = commands.handle("/clear", messages)
        assert result is True
        assert len(messages) == 1
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] != "old system prompt"

    def test_clear_alias(self, messages: list[dict[str, Any]]) -> None:
        assert commands.handle("/c", messages) is True
        assert len(messages) == 1


class TestUnknownAndPassthrough:
    def test_unknown_slash_is_handled(self, capsys: pytest.CaptureFixture[str]) -> None:
        # Unknown slash commands are reported and stay in the REPL — they
        # must NOT fall through to the model.
        result = commands.handle("/nope", [])
        out = capsys.readouterr().out
        assert result is True
        assert "Unknown command" in out
        assert "/nope" in out

    def test_plain_text_falls_through(self) -> None:
        assert commands.handle("hello world", []) is None

    def test_empty_input_falls_through(self) -> None:
        assert commands.handle("   ", []) is None
