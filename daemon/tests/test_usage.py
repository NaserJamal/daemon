"""Tests for the token-usage tracker and the /usage slash command."""

from __future__ import annotations

from typing import Any

import pytest
from daemon.cli import commands
from daemon.core import usage


@pytest.fixture(autouse=True)
def _reset_usage() -> None:
    """Each test starts with a clean tracker and per-turn display off."""
    usage.reset()
    usage.set_show_per_turn(False)


class TestTracker:
    def test_starts_empty(self) -> None:
        u = usage.current()
        assert u.input_tokens == 0
        assert u.output_tokens == 0
        assert u.requests == 0
        assert u.total_tokens == 0

    def test_add_response_accumulates(self) -> None:
        usage.add_response({"usage": {"prompt_tokens": 10, "completion_tokens": 4}})
        usage.add_response({"usage": {"prompt_tokens": 7, "completion_tokens": 3}})
        u = usage.current()
        assert u.input_tokens == 17
        assert u.output_tokens == 7
        assert u.total_tokens == 24
        assert u.requests == 2

    def test_missing_or_malformed_usage_is_ignored(self) -> None:
        usage.add_response({})
        usage.add_response({"usage": None})
        usage.add_response({"usage": "not-a-dict"})
        usage.add_response({"usage": {"prompt_tokens": "abc"}})
        u = usage.current()
        # Three calls had no parseable block; the fourth had a string token
        # value that coerces to 0 but still counts as a request.
        assert u.input_tokens == 0
        assert u.output_tokens == 0
        assert u.requests == 1

    def test_reset_zeroes_counters(self) -> None:
        usage.add_response({"usage": {"prompt_tokens": 5, "completion_tokens": 2}})
        usage.reset()
        assert usage.current().total_tokens == 0
        assert usage.current().requests == 0

    def test_format_summary_empty(self) -> None:
        assert "no usage" in usage.format_summary()

    def test_format_summary_populated(self) -> None:
        usage.add_response({"usage": {"prompt_tokens": 1234, "completion_tokens": 56}})
        summary = usage.format_summary()
        assert "1,234" in summary
        assert "56" in summary
        assert "1 request" in summary

    def test_show_per_turn_toggle(self) -> None:
        assert usage.show_per_turn() is False
        usage.set_show_per_turn(True)
        assert usage.show_per_turn() is True
        usage.set_show_per_turn(False)
        assert usage.show_per_turn() is False


class TestUsageCommand:
    def _messages(self) -> list[dict[str, Any]]:
        return [{"role": "system", "content": "x"}]

    def test_prints_current_totals(self, capsys: pytest.CaptureFixture[str]) -> None:
        usage.add_response({"usage": {"prompt_tokens": 11, "completion_tokens": 22}})
        result = commands.handle("/usage", self._messages())
        assert result is True
        out = capsys.readouterr().out
        assert "11" in out
        assert "22" in out

    def test_alias(self, capsys: pytest.CaptureFixture[str]) -> None:
        result = commands.handle("/u", self._messages())
        assert result is True
        assert "no usage" in capsys.readouterr().out

    def test_on_off_toggles(self, capsys: pytest.CaptureFixture[str]) -> None:
        commands.handle("/usage on", self._messages())
        assert usage.show_per_turn() is True
        commands.handle("/usage off", self._messages())
        assert usage.show_per_turn() is False
        out = capsys.readouterr().out
        assert "on" in out
        assert "off" in out

    def test_invalid_arg_warns(self, capsys: pytest.CaptureFixture[str]) -> None:
        result = commands.handle("/usage maybe", self._messages())
        assert result is True
        assert "Usage:" in capsys.readouterr().out

    def test_clear_resets_usage(self) -> None:
        usage.add_response({"usage": {"prompt_tokens": 9, "completion_tokens": 1}})
        commands.handle("/clear", self._messages())
        assert usage.current().total_tokens == 0
