"""Tests for the oversized-output spill helper."""

from __future__ import annotations

import re
from pathlib import Path
from unittest.mock import patch

from daemon.utils.spill import MAX_INLINE_LINES, spill


def _big(lines: int) -> str:
    return "\n".join(f"line {i}" for i in range(lines))


def _saved_path(result: str) -> Path:
    match = re.search(r"full output: (\S+) -", result)
    assert match, result
    return Path(match.group(1))


class TestSpill:
    def test_small_output_passes_through(self) -> None:
        assert spill("hello\nworld", "bash") == "hello\nworld"

    def test_line_threshold_is_inclusive(self) -> None:
        text = _big(MAX_INLINE_LINES)
        assert spill(text, "bash") == text

    def test_long_output_is_written_to_a_file(self) -> None:
        text = _big(MAX_INLINE_LINES + 1)
        result = spill(text, "bash")
        assert _saved_path(result).read_text(encoding="utf-8") == text
        assert len(result) < len(text)

    def test_wide_output_spills_on_chars_alone(self) -> None:
        text = "x" * 60_000
        result = spill(text, "bash")
        assert _saved_path(result).read_text(encoding="utf-8") == text

    def test_preview_keeps_both_ends(self) -> None:
        result = spill(_big(3_000), "bash")
        assert "line 0" in result
        assert "line 2999" in result
        assert "line 1500" not in result
        assert "2930 lines omitted" in result

    def test_label_prefixes_the_filename(self) -> None:
        result = spill(_big(3_000), "fetch example.com")
        assert _saved_path(result).name.startswith("fetch-example.com-")

    def test_each_call_gets_its_own_file(self) -> None:
        first = _saved_path(spill(_big(3_000), "bash"))
        second = _saved_path(spill(_big(3_000), "bash"))
        assert first != second

    def test_write_failure_still_returns_a_preview(self) -> None:
        with patch("daemon.utils.spill._write", side_effect=OSError("disk full")):
            result = spill(_big(3_000), "bash")
        assert "could not be saved: disk full" in result
        assert "line 0" in result
