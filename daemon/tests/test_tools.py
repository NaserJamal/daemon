"""Tests for tools and danger detection.

Run with: PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest daemon/tests/
"""

from __future__ import annotations

from typing import Any

from daemon.safety.danger import danger_reason
from daemon.tools import run_tool


class TestReadTool:
    def test_read_file(self, tmp_path: Any) -> None:
        f = tmp_path / "test.txt"
        f.write_text("Line 1\nLine 2\nLine 3\n")
        result = run_tool("read", {"path": str(f)})
        assert "1| Line 1" in result
        assert "2| Line 2" in result
        assert "3| Line 3" in result
        assert "end of file" in result

    def test_read_with_offset(self, tmp_path: Any) -> None:
        f = tmp_path / "test.txt"
        f.write_text("Line 1\nLine 2\nLine 3\nLine 4\n")
        result = run_tool("read", {"path": str(f), "offset": 2, "limit": 2})
        assert "2| Line 2" in result
        assert "3| Line 3" in result

    def test_read_binary_file(self, tmp_path: Any) -> None:
        f = tmp_path / "test.bin"
        f.write_bytes(b"\x00\x01\x02\x00")
        result = run_tool("read", {"path": str(f)})
        assert "binary" in result.lower()


class TestWriteTool:
    def test_write_file(self, tmp_path: Any) -> None:
        f = tmp_path / "output.txt"
        assert run_tool("write", {"path": str(f), "content": "Hello, World!"}) == "ok"
        assert f.read_text() == "Hello, World!"

    def test_overwrite_file(self, tmp_path: Any) -> None:
        f = tmp_path / "output.txt"
        f.write_text("Old content")
        assert run_tool("write", {"path": str(f), "content": "New content"}) == "ok"
        assert f.read_text() == "New content"


class TestEditTool:
    def test_edit_simple(self, tmp_path: Any) -> None:
        f = tmp_path / "test.txt"
        f.write_text("Hello World")
        assert run_tool("edit", {"path": str(f), "old": "World", "new": "Universe"}) == "ok"
        assert f.read_text() == "Hello Universe"

    def test_edit_identical(self, tmp_path: Any) -> None:
        f = tmp_path / "test.txt"
        f.write_text("Hello")
        result = run_tool("edit", {"path": str(f), "old": "Hello", "new": "Hello"})
        assert "identical" in result.lower()

    def test_edit_not_found(self, tmp_path: Any) -> None:
        f = tmp_path / "test.txt"
        f.write_text("Hello World")
        result = run_tool("edit", {"path": str(f), "old": "NotFound", "new": "Replaced"})
        assert "not found" in result.lower()

    def test_edit_create_mode(self, tmp_path: Any) -> None:
        f = tmp_path / "new.txt"
        result = run_tool("edit", {"path": str(f), "old": "", "new": "New content"})
        assert "created" in result
        assert f.read_text() == "New content"


class TestGlobTool:
    def test_glob_pattern(self, tmp_path: Any) -> None:
        (tmp_path / "test1.txt").touch()
        (tmp_path / "test2.txt").touch()
        (tmp_path / "test.py").touch()
        result = run_tool("glob", {"pattern": "*.txt", "path": str(tmp_path)})
        assert "test1.txt" in result
        assert "test2.txt" in result
        assert "test.py" not in result

    def test_glob_none(self, tmp_path: Any) -> None:
        assert run_tool("glob", {"pattern": "nonexistent.*", "path": str(tmp_path)}) == "none"


class TestGrepTool:
    def test_grep_simple(self, tmp_path: Any) -> None:
        (tmp_path / "test.py").write_text("def hello():\n    pass\ndef world():\n    pass\n")
        result = run_tool("grep", {"pattern": "def", "path": str(tmp_path)})
        assert "test.py" in result
        assert ":1:" in result
        assert ":3:" in result

    def test_grep_none(self, tmp_path: Any) -> None:
        (tmp_path / "test.txt").write_text("hello world")
        assert run_tool("grep", {"pattern": "xyz123", "path": str(tmp_path)}) == "none"

    def test_grep_skips_binary(self, tmp_path: Any) -> None:
        (tmp_path / "test.bin").write_bytes(b"\x00\x01def\x02")
        assert run_tool("grep", {"pattern": "def", "path": str(tmp_path)}) == "none"


class TestDangerDetection:
    def test_rm_detection(self) -> None:
        assert danger_reason("rm file.txt") == "rm"
        assert danger_reason("rm -rf /tmp") == "rm"
        assert danger_reason("rmdir /tmp") == "rmdir"

    def test_safe_commands(self) -> None:
        assert danger_reason("ls -la") is None
        assert danger_reason("pwd") is None
        assert danger_reason("cat file.txt") is None

    def test_fork_bomb(self) -> None:
        assert danger_reason(":(){ :|:& };:") == "fork bomb"

    def test_git_destructive(self) -> None:
        assert danger_reason("git reset --hard") == "git reset --hard"
        assert danger_reason("git push --force") == "git force push"
        assert danger_reason("git clean -f") == "git clean -f"
