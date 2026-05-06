"""Tests for debug-mode API logging."""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from daemon.cli.main import _consume_debug_flag
from daemon.core import api, debug
from daemon.core.config import Settings


@pytest.fixture(autouse=True)
def _isolated_log() -> Iterator[None]:
    """Ensure each test starts with debug disabled and restores after."""
    debug.disable()
    yield
    debug.disable()


class _MockResponse:
    def __init__(self, payload: bytes) -> None:
        self._payload = payload

    def __enter__(self) -> _MockResponse:
        return self

    def __exit__(self, *_: Any) -> None:
        return None

    def read(self) -> bytes:
        return self._payload


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def _settings() -> Settings:
    return Settings(api_key="x", base_url="https://example.test", model_name="m")


class TestModule:
    def test_disabled_by_default(self) -> None:
        assert not debug.is_enabled()
        debug.log_event("noop", {"x": 1})  # must not raise

    def test_enable_writes_default_filename(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        path = debug.enable()
        assert path == tmp_path / debug.DEFAULT_FILENAME
        assert path.exists()
        records = _read_jsonl(path)
        assert records[0]["kind"] == "enabled"

    def test_enable_with_explicit_path(self, tmp_path: Path) -> None:
        path = tmp_path / "sub" / "log.jsonl"
        debug.enable(path)
        assert path.exists()

    def test_log_event_appends_jsonl(self, tmp_path: Path) -> None:
        path = tmp_path / "log"
        debug.enable(path)
        debug.log_event("request", {"a": 1})
        debug.log_event("response", {"b": 2})
        records = _read_jsonl(path)
        kinds = [r["kind"] for r in records]
        assert kinds == ["enabled", "request", "response"]
        assert records[1]["data"] == {"a": 1}
        assert records[2]["data"] == {"b": 2}
        assert all("ts" in r for r in records)

    def test_disable_stops_writes(self, tmp_path: Path) -> None:
        path = tmp_path / "log"
        debug.enable(path)
        debug.disable()
        assert not debug.is_enabled()
        debug.log_event("late", {})
        # Only the "enabled" line should be present.
        assert len(_read_jsonl(path)) == 1

    def test_from_env_truthy(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("DAEMON_DEBUG", "1")
        path = debug.from_env()
        assert path == tmp_path / debug.DEFAULT_FILENAME

    def test_from_env_explicit_path(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        target = tmp_path / "custom.log"
        monkeypatch.setenv("DAEMON_DEBUG", str(target))
        path = debug.from_env()
        assert path == target

    def test_from_env_unset(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("DAEMON_DEBUG", raising=False)
        assert debug.from_env() is None
        assert not debug.is_enabled()


class TestApiIntegration:
    def test_request_and_response_logged(self, tmp_path: Path) -> None:
        path = tmp_path / "log"
        debug.enable(path)
        body = {"choices": [{"message": {"role": "assistant", "content": "hi"}}]}
        with patch(
            "daemon.core.api.urllib.request.urlopen",
            return_value=_MockResponse(json.dumps(body).encode()),
        ):
            api.call_api([{"role": "user", "content": "hi"}], tools=[], settings=_settings())
        records = _read_jsonl(path)
        kinds = [r["kind"] for r in records]
        assert kinds == ["enabled", "request", "response"]
        req = records[1]["data"]
        assert req["url"] == "https://example.test/chat/completions"
        assert req["body"]["model"] == "m"
        assert req["body"]["messages"] == [{"role": "user", "content": "hi"}]
        assert records[2]["data"] == body

    def test_no_log_when_disabled(self, tmp_path: Path) -> None:
        # Logging never happens; we only assert the call still works.
        body = {"choices": [{"message": {"role": "assistant", "content": "hi"}}]}
        with patch(
            "daemon.core.api.urllib.request.urlopen",
            return_value=_MockResponse(json.dumps(body).encode()),
        ):
            result = api.call_api([], tools=[], settings=_settings())
        assert result == body
        assert not (tmp_path / debug.DEFAULT_FILENAME).exists()


class TestCliFlagParsing:
    def test_consume_debug_bare_enables_default_path(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("DAEMON_DEBUG", raising=False)
        remaining = _consume_debug_flag(["--debug", "--continue"])
        assert remaining == ["--continue"]
        assert debug.is_enabled()
        assert debug.current_path() == tmp_path / debug.DEFAULT_FILENAME

    def test_consume_debug_with_value(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("DAEMON_DEBUG", raising=False)
        target = tmp_path / "x.log"
        remaining = _consume_debug_flag(["--debug", str(target), "configure"])
        assert remaining == ["configure"]
        assert debug.current_path() == target

    def test_consume_debug_equals_form(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("DAEMON_DEBUG", raising=False)
        target = tmp_path / "y.log"
        remaining = _consume_debug_flag([f"--debug={target}"])
        assert remaining == []
        assert debug.current_path() == target

    def test_consume_no_flag_falls_back_to_env(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        target = tmp_path / "z.log"
        monkeypatch.setenv("DAEMON_DEBUG", str(target))
        remaining = _consume_debug_flag(["--continue"])
        assert remaining == ["--continue"]
        assert debug.current_path() == target

    def test_consume_no_flag_no_env_stays_disabled(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("DAEMON_DEBUG", raising=False)
        remaining = _consume_debug_flag(["--resume"])
        assert remaining == ["--resume"]
        assert not debug.is_enabled()
