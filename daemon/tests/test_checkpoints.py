"""Tests for the file-checkpoint stack and the /undo slash command."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from daemon.cli import commands
from daemon.core import checkpoints


@pytest.fixture(autouse=True)
def _reset_stack() -> Iterator[None]:
    """Module state is process-wide; isolate each test."""
    checkpoints.clear()
    yield
    checkpoints.clear()


class TestSnapshot:
    def test_existing_file(self, tmp_path: Path) -> None:
        f = tmp_path / "hello.txt"
        f.write_bytes(b"original")
        content, existed = checkpoints.snapshot(str(f))
        assert existed is True
        assert content == b"original"

    def test_missing_file(self, tmp_path: Path) -> None:
        content, existed = checkpoints.snapshot(str(tmp_path / "ghost.txt"))
        assert existed is False
        assert content is None


class TestPushAndUndo:
    def test_undo_restores_existing_file(self, tmp_path: Path) -> None:
        f = tmp_path / "f.txt"
        f.write_bytes(b"v1")
        content, _ = checkpoints.snapshot(str(f))
        f.write_bytes(b"v2")
        checkpoints.push(str(f), "write", content)

        cp = checkpoints.undo()
        assert cp is not None
        assert cp.tool == "write"
        assert f.read_bytes() == b"v1"
        assert checkpoints.count() == 0

    def test_undo_deletes_file_that_did_not_exist(self, tmp_path: Path) -> None:
        f = tmp_path / "new.txt"
        checkpoints.push(str(f), "write", None)
        f.write_bytes(b"created")

        cp = checkpoints.undo()
        assert cp is not None
        assert cp.content is None
        assert not f.exists()

    def test_undo_when_empty_returns_none(self) -> None:
        assert checkpoints.undo() is None

    def test_undo_is_lifo(self, tmp_path: Path) -> None:
        a = tmp_path / "a.txt"
        b = tmp_path / "b.txt"
        a.write_bytes(b"a-original")
        b.write_bytes(b"b-original")
        checkpoints.push(str(a), "edit", b"a-original")
        checkpoints.push(str(b), "edit", b"b-original")
        a.write_bytes(b"a-mutated")
        b.write_bytes(b"b-mutated")

        first = checkpoints.undo()
        second = checkpoints.undo()
        assert first is not None and first.path == str(b)
        assert second is not None and second.path == str(a)
        assert a.read_bytes() == b"a-original"
        assert b.read_bytes() == b"b-original"

    def test_undo_missing_target_is_safe(self, tmp_path: Path) -> None:
        # If the file vanished between checkpoint and undo, deleting a
        # "didn't exist before" snapshot must not raise.
        f = tmp_path / "vanished.txt"
        checkpoints.push(str(f), "write", None)
        # File never created; undo should still pop without error.
        cp = checkpoints.undo()
        assert cp is not None
        assert not f.exists()


class TestClear:
    def test_clear_empties_stack(self, tmp_path: Path) -> None:
        f = tmp_path / "f.txt"
        checkpoints.push(str(f), "write", b"x")
        assert checkpoints.count() == 1
        checkpoints.clear()
        assert checkpoints.count() == 0
        assert checkpoints.undo() is None


class TestUndoCommand:
    def test_undo_with_nothing_to_undo(self, capsys: pytest.CaptureFixture[str]) -> None:
        result = commands.handle("/undo", [])
        assert result is True
        assert "Nothing to undo" in capsys.readouterr().out

    def test_undo_restores_and_reports(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        f = tmp_path / "f.txt"
        f.write_bytes(b"v1")
        checkpoints.push(str(f), "edit", b"v1")
        f.write_bytes(b"v2")

        result = commands.handle("/undo", [])
        out = capsys.readouterr().out
        assert result is True
        assert f.read_bytes() == b"v1"
        assert "restored" in out
        assert str(f) in out

    def test_undo_after_create_reports_deletion(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        f = tmp_path / "new.txt"
        checkpoints.push(str(f), "write", None)
        f.write_bytes(b"created")

        commands.handle("/undo", [])
        out = capsys.readouterr().out
        assert "deleted" in out
        assert not f.exists()

    def test_clear_command_drops_checkpoints(self, tmp_path: Path) -> None:
        f = tmp_path / "f.txt"
        checkpoints.push(str(f), "write", b"x")
        # /clear must reset the stack alongside messages and usage.
        msgs: list[dict[str, Any]] = [{"role": "system", "content": "sys"}]
        commands.handle("/clear", msgs)
        assert checkpoints.count() == 0
