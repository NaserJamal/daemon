"""Tests for unified-diff formatting of write/edit tool results."""

from __future__ import annotations

from daemon.core.diff import format_diff


class TestFormatDiff:
    def test_new_file(self) -> None:
        result = format_diff("foo.txt", None, b"hello\nworld\n")
        head, _, body = result.partition("\n")
        assert head == "+2 -0"
        assert "+hello" in body
        assert "+world" in body

    def test_modification(self) -> None:
        pre = b"alpha\nbeta\ngamma\n"
        post = b"alpha\nBETA\ngamma\n"
        result = format_diff("foo.txt", pre, post)
        head, _, body = result.partition("\n")
        assert head == "+1 -1"
        assert "-beta" in body
        assert "+BETA" in body
        assert "alpha" in body  # context

    def test_no_change(self) -> None:
        assert format_diff("foo.txt", b"same\n", b"same\n") == "ok (no change)"

    def test_no_change_for_missing_to_empty(self) -> None:
        # A `write` of "" into a file that didn't exist still produces
        # zero-byte equality and should report no change.
        assert format_diff("foo.txt", None, b"") == "ok (no change)"

    def test_binary_pre(self) -> None:
        assert format_diff("foo.bin", b"\xff\xfe", b"text\n") == "ok (binary)"

    def test_binary_post(self) -> None:
        assert format_diff("foo.bin", b"text\n", b"\xff\xfe") == "ok (binary)"

    def test_pure_addition_counts(self) -> None:
        pre = b"line1\n"
        post = b"line1\nline2\nline3\n"
        head = format_diff("foo.txt", pre, post).split("\n", 1)[0]
        assert head == "+2 -0"

    def test_pure_deletion_counts(self) -> None:
        pre = b"line1\nline2\nline3\n"
        post = b"line1\n"
        head = format_diff("foo.txt", pre, post).split("\n", 1)[0]
        assert head == "+0 -2"

    def test_path_in_diff_header(self) -> None:
        result = format_diff("a/b/c.py", b"x\n", b"y\n")
        assert "--- a/b/c.py" in result
        assert "+++ a/b/c.py" in result
