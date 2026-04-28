"""
Tests for nanocode tools.

Run with: pytest nanocode/tests/
"""

from __future__ import annotations

import os
import tempfile
from typing import Any

import pytest

# Set up test environment
os.environ["NANOCODE_YOLO"] = "1"


class TestReadTool:
    """Tests for the ReadTool."""

    def test_read_file(self, tmp_path: Any) -> None:
        """Test reading a simple file."""
        from nanocode.tools import run_tool

        # Create test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("Line 1\nLine 2\nLine 3\n")

        result = run_tool("read", {"path": str(test_file)})

        assert "1| Line 1" in result
        assert "2| Line 2" in result
        assert "3| Line 3" in result
        assert "end of file" in result

    def test_read_with_offset(self, tmp_path: Any) -> None:
        """Test reading with offset."""
        from nanocode.tools import run_tool

        test_file = tmp_path / "test.txt"
        test_file.write_text("Line 1\nLine 2\nLine 3\nLine 4\n")

        result = run_tool("read", {"path": str(test_file), "offset": 2, "limit": 2})

        assert "2| Line 2" in result
        assert "3| Line 3" in result

    def test_read_binary_file(self, tmp_path: Any) -> None:
        """Test reading a binary file."""
        from nanocode.tools import run_tool

        test_file = tmp_path / "test.bin"
        test_file.write_bytes(b"\x00\x01\x02\x00")

        result = run_tool("read", {"path": str(test_file)})

        assert "error" in result.lower()
        assert "binary" in result.lower()


class TestWriteTool:
    """Tests for the WriteTool."""

    def test_write_file(self, tmp_path: Any) -> None:
        """Test writing to a file."""
        from nanocode.tools import run_tool

        test_file = tmp_path / "output.txt"
        result = run_tool("write", {"path": str(test_file), "content": "Hello, World!"})

        assert result == "ok"
        assert test_file.read_text() == "Hello, World!"

    def test_overwrite_file(self, tmp_path: Any) -> None:
        """Test overwriting an existing file."""
        from nanocode.tools import run_tool

        test_file = tmp_path / "output.txt"
        test_file.write_text("Old content")

        result = run_tool("write", {"path": str(test_file), "content": "New content"})

        assert result == "ok"
        assert test_file.read_text() == "New content"


class TestEditTool:
    """Tests for the EditTool."""

    def test_edit_simple(self, tmp_path: Any) -> None:
        """Test simple text replacement."""
        from nanocode.tools import run_tool

        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello World")

        result = run_tool(
            "edit",
            {"path": str(test_file), "old": "World", "new": "Universe"}
        )

        assert result == "ok"
        assert test_file.read_text() == "Hello Universe"

    def test_edit_identical(self, tmp_path: Any) -> None:
        """Test that identical old and new returns error."""
        from nanocode.tools import run_tool

        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello")

        result = run_tool(
            "edit",
            {"path": str(test_file), "old": "Hello", "new": "Hello"}
        )

        assert "error" in result.lower()
        assert "identical" in result.lower()

    def test_edit_not_found(self, tmp_path: Any) -> None:
        """Test editing text that doesn't exist."""
        from nanocode.tools import run_tool

        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello World")

        result = run_tool(
            "edit",
            {"path": str(test_file), "old": "NotFound", "new": "Replaced"}
        )

        assert "error" in result.lower()
        assert "not found" in result.lower()

    def test_edit_create_mode(self, tmp_path: Any) -> None:
        """Test creating file with empty old."""
        from nanocode.tools import run_tool

        test_file = tmp_path / "new.txt"
        result = run_tool(
            "edit",
            {"path": str(test_file), "old": "", "new": "New content"}
        )

        assert "created" in result
        assert test_file.read_text() == "New content"


class TestGlobTool:
    """Tests for the GlobTool."""

    def test_glob_pattern(self, tmp_path: Any) -> None:
        """Test glob pattern matching."""
        from nanocode.tools import run_tool

        # Create test files
        (tmp_path / "test1.txt").touch()
        (tmp_path / "test2.txt").touch()
        (tmp_path / "test.py").touch()

        result = run_tool("glob", {"pattern": "*.txt", "path": str(tmp_path)})

        assert "test1.txt" in result
        assert "test2.txt" in result
        assert "test.py" not in result

    def test_glob_none(self, tmp_path: Any) -> None:
        """Test glob with no matches."""
        from nanocode.tools import run_tool

        result = run_tool("glob", {"pattern": "nonexistent.*", "path": str(tmp_path)})

        assert result == "none"


class TestGrepTool:
    """Tests for the GrepTool."""

    def test_grep_simple(self, tmp_path: Any) -> None:
        """Test simple grep."""
        from nanocode.tools import run_tool

        test_file = tmp_path / "test.py"
        test_file.write_text("def hello():\n    pass\ndef world():\n    pass\n")

        result = run_tool("grep", {"pattern": "def", "path": str(tmp_path)})

        assert "test.py" in result
        assert ":1:" in result
        assert ":3:" in result

    def test_grep_none(self, tmp_path: Any) -> None:
        """Test grep with no matches."""
        from nanocode.tools import run_tool

        test_file = tmp_path / "test.txt"
        test_file.write_text("hello world")

        result = run_tool("grep", {"pattern": "xyz123", "path": str(tmp_path)})

        assert result == "none"

    def test_grep_skips_binary(self, tmp_path: Any) -> None:
        """Test that grep skips binary files."""
        from nanocode.tools import run_tool

        test_file = tmp_path / "test.bin"
        test_file.write_bytes(b"\x00\x01def\x02")

        result = run_tool("grep", {"pattern": "def", "path": str(tmp_path)})

        assert result == "none"


class TestDangerDetection:
    """Tests for danger pattern detection."""

    def test_rm_detection(self) -> None:
        """Test detection of rm commands."""
        from nanocode.safety.danger import danger_reason

        assert danger_reason("rm file.txt") == "rm"
        assert danger_reason("rm -rf /tmp") == "rm"
        assert danger_reason("rmdir /tmp") == "rmdir"

    def test_safe_commands(self) -> None:
        """Test that safe commands return None."""
        from nanocode.safety.danger import danger_reason

        assert danger_reason("ls -la") is None
        assert danger_reason("pwd") is None
        assert danger_reason("cat file.txt") is None

    def test_fork_bomb(self) -> None:
        """Test detection of fork bombs."""
        from nanocode.safety.danger import danger_reason

        assert danger_reason(":(){ :|:& };:") == "fork bomb"

    def test_git_destructive(self) -> None:
        """Test detection of destructive git commands."""
        from nanocode.safety.danger import danger_reason

        assert danger_reason("git reset --hard") == "git reset --hard"
        assert danger_reason("git push --force") == "git force push"
        assert danger_reason("git clean -f") == "git clean -f"


class TestSession:
    """Tests for Session management."""

    def test_session_initialization(self) -> None:
        """Test session starts with system message."""
        from nanocode.core.session import Session

        session = Session()
        assert len(session) == 1
        assert session.messages[0]["role"] == "system"

    def test_add_user(self) -> None:
        """Test adding user messages."""
        from nanocode.core.session import Session

        session = Session()
        session.add_user("Hello")
        assert len(session) == 2
        assert session.messages[-1]["role"] == "user"
        assert session.messages[-1]["content"] == "Hello"

    def test_add_assistant(self) -> None:
        """Test adding assistant messages."""
        from nanocode.core.session import Session

        session = Session()
        session.add_assistant("Hi there!")
        assert len(session) == 2
        assert session.messages[-1]["role"] == "assistant"
        assert session.messages[-1]["content"] == "Hi there!"

    def test_clear(self) -> None:
        """Test clearing session."""
        from nanocode.core.session import Session

        session = Session()
        session.add_user("Hello")
        session.add_assistant("Hi")
        assert len(session) == 3

        session.clear()
        assert len(session) == 1
        assert session.messages[0]["role"] == "system"

    def test_serialize(self) -> None:
        """Test session serialization."""
        from nanocode.core.session import Session

        session = Session()
        session.add_user("Hello")

        data = session.serialize()
        assert '"role": "user"' in data
        assert '"Hello"' in data
