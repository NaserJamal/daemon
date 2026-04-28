"""Tests for the conversation persistence module and session-related commands."""

from __future__ import annotations

import json
import os
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from daemon.cli import commands
from daemon.core import sessions


@pytest.fixture
def isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """Point the user-config dir (and so the projects dir) at a tmp path."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setenv("APPDATA", str(tmp_path))
    monkeypatch.setattr("daemon.core.user_config.config_dir", lambda: tmp_path / "daemon")
    yield tmp_path


@pytest.fixture
def cwd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Run each test in a deterministic cwd so encode_cwd is stable."""
    work = tmp_path / "work"
    work.mkdir()
    monkeypatch.chdir(work)
    return Path(os.getcwd())


@pytest.fixture(autouse=True)
def _reset_session_state() -> Iterator[None]:
    """Don't let one test's active session leak into the next."""
    commands.set_session(None)
    yield
    commands.set_session(None)


class TestEncodeCwd:
    def test_replaces_non_alphanumeric_with_dash(self) -> None:
        assert sessions.encode_cwd("/home/user/project") == "home-user-project"

    def test_collapses_runs(self) -> None:
        assert sessions.encode_cwd("/a//b") == "a-b"

    def test_empty_falls_back(self) -> None:
        assert sessions.encode_cwd("///") == "root"


class TestSessionRoundTrip:
    def test_new_then_open_replays_messages(self, isolated_home: Path, cwd: Path) -> None:
        session = sessions.Session.new()
        msgs: list[dict[str, Any]] = [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "hello"},
        ]
        session.sync(msgs)

        reopened, restored = sessions.Session.open(session.path)
        assert restored == msgs
        assert reopened.session_id == session.session_id
        assert reopened.cwd == str(cwd)

    def test_sync_only_appends_new_messages(self, isolated_home: Path, cwd: Path) -> None:
        session = sessions.Session.new()
        msgs: list[dict[str, Any]] = [{"role": "user", "content": "a"}]
        session.sync(msgs)
        msgs.append({"role": "assistant", "content": "b"})
        session.sync(msgs)
        msgs.append({"role": "user", "content": "c"})
        session.sync(msgs)

        with session.path.open() as f:
            line_count = sum(1 for _ in f)
        # 1 header + 3 messages
        assert line_count == 4
        _, restored = sessions.Session.open(session.path)
        assert restored == msgs

    def test_rewrite_truncates(self, isolated_home: Path, cwd: Path) -> None:
        session = sessions.Session.new()
        msgs: list[dict[str, Any]] = [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "hello"},
        ]
        session.sync(msgs)
        truncated = msgs[:1]
        session.rewrite(truncated)

        _, restored = sessions.Session.open(session.path)
        assert restored == truncated

    def test_corrupt_lines_are_skipped(self, isolated_home: Path, cwd: Path) -> None:
        session = sessions.Session.new()
        session.sync([{"role": "user", "content": "ok"}])
        with session.path.open("a", encoding="utf-8") as f:
            f.write("not json\n")
            f.write(
                json.dumps({"type": "message", "message": {"role": "user", "content": "good"}})
                + "\n"
            )
        _, msgs = sessions.Session.open(session.path)
        assert [m["content"] for m in msgs] == ["ok", "good"]


class TestListSessions:
    def test_empty_when_no_sessions(self, isolated_home: Path, cwd: Path) -> None:
        assert sessions.list_sessions() == []

    def test_lists_only_current_cwd(
        self, isolated_home: Path, cwd: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Session in `cwd`.
        s1 = sessions.Session.new()
        s1.sync([{"role": "user", "content": "in-cwd"}])
        # Session in another directory.
        other = tmp_path / "elsewhere"
        other.mkdir()
        monkeypatch.chdir(other)
        s2 = sessions.Session.new()
        s2.sync([{"role": "user", "content": "elsewhere"}])

        # Listing for `other` should return only its session.
        metas = sessions.list_sessions()
        assert [m.session_id for m in metas] == [s2.session_id]

        # Listing for `cwd` should return only the first.
        monkeypatch.chdir(cwd)
        metas = sessions.list_sessions()
        assert [m.session_id for m in metas] == [s1.session_id]

    def test_summary_uses_first_user_message(self, isolated_home: Path, cwd: Path) -> None:
        session = sessions.Session.new()
        session.sync(
            [
                {"role": "system", "content": "sys"},
                {"role": "user", "content": "the question"},
                {"role": "assistant", "content": "the answer"},
            ]
        )
        metas = sessions.list_sessions()
        assert len(metas) == 1
        assert metas[0].summary == "the question"
        assert metas[0].message_count == 3

    def test_sorted_newest_first(self, isolated_home: Path, cwd: Path) -> None:
        s1 = sessions.Session.new()
        s1.sync([{"role": "user", "content": "older"}])
        s2 = sessions.Session.new()
        s2.sync([{"role": "user", "content": "newer"}])
        # Force s2 to look newer than s1.
        os.utime(s1.path, (1, 1))
        os.utime(s2.path, (2, 2))
        metas = sessions.list_sessions()
        assert metas[0].session_id == s2.session_id


class TestFormatAge:
    def test_seconds(self) -> None:
        assert sessions.format_age(now=100.0, updated_at=70.0) == "30s"

    def test_minutes(self) -> None:
        assert sessions.format_age(now=1000.0, updated_at=700.0) == "5m"

    def test_hours(self) -> None:
        assert sessions.format_age(now=10_000.0, updated_at=2_800.0) == "2h"

    def test_days(self) -> None:
        assert sessions.format_age(now=200_000.0, updated_at=10_000.0) == "2d"


class TestRewindCommand:
    def test_no_user_messages(
        self, isolated_home: Path, cwd: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        session = sessions.Session.new()
        commands.set_session(session)
        msgs: list[dict[str, Any]] = [{"role": "system", "content": "sys"}]
        session.sync(msgs)
        result = commands.handle("/rewind", msgs)
        assert result is True
        assert "Nothing to rewind" in capsys.readouterr().out

    def test_rewind_truncates_and_rewrites_file(self, isolated_home: Path, cwd: Path) -> None:
        session = sessions.Session.new()
        commands.set_session(session)
        msgs: list[dict[str, Any]] = [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "first"},
            {"role": "assistant", "content": "ack"},
            {"role": "user", "content": "second"},
            {"role": "assistant", "content": "ack2"},
        ]
        session.sync(msgs)

        result = commands.handle("/rewind 2", msgs)
        assert result is True
        assert msgs == [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "first"},
            {"role": "assistant", "content": "ack"},
        ]
        # Session file matches the in-memory state after rewrite.
        _, restored = sessions.Session.open(session.path)
        assert restored == msgs

    def test_rewind_rejects_out_of_range(
        self, isolated_home: Path, cwd: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        session = sessions.Session.new()
        commands.set_session(session)
        msgs: list[dict[str, Any]] = [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "only"},
        ]
        session.sync(msgs)
        # No prompt should fire (we passed an arg) — and it should reject.
        result = commands.handle("/rewind 99", msgs)
        out = capsys.readouterr().out
        assert result is True
        assert "Invalid selection" in out
        # Messages untouched.
        assert len(msgs) == 2


class TestClearStartsNewSession:
    def test_clear_swaps_session_and_preserves_old_file(
        self, isolated_home: Path, cwd: Path
    ) -> None:
        session = sessions.Session.new()
        commands.set_session(session)
        msgs: list[dict[str, Any]] = [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "hi"},
        ]
        session.sync(msgs)
        old_path = session.path

        commands.handle("/clear", msgs)
        new_session = commands.get_session()
        assert new_session is not None
        assert new_session.session_id != session.session_id
        # Old transcript still on disk.
        _, restored = sessions.Session.open(old_path)
        assert restored[-1]["content"] == "hi"
