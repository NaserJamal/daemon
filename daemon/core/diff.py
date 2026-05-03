"""Format unified diffs for `write` and `edit` tool results.

The CLI snapshots each target file before a `write` or `edit` runs (the
same pre-image used by `/undo`). After the tool succeeds we read the
post-image, hand both halves to `format_diff`, and replace the tool's
"ok" with the resulting diff string. The model and the user-facing
preview both consume the same text.
"""

from __future__ import annotations

import difflib


def _decode(content: bytes | None) -> str | None:
    """Return UTF-8 text for the given bytes, "" for None, or None for binary."""
    if content is None:
        return ""
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError:
        return None


def format_diff(path: str, pre: bytes | None, post: bytes) -> str:
    """Build a unified-diff string for the change at ``path``.

    Returns ``"ok (no change)"`` when the contents are identical and
    ``"ok (binary)"`` when either side isn't valid UTF-8. Otherwise the
    first line is a ``+N -M`` summary and the remainder is the unified
    diff body produced by :mod:`difflib`.
    """
    pre_text = _decode(pre)
    post_text = _decode(post)
    if pre_text is None or post_text is None:
        return "ok (binary)"
    if pre_text == post_text:
        return "ok (no change)"

    diff = list(
        difflib.unified_diff(
            pre_text.splitlines(keepends=True),
            post_text.splitlines(keepends=True),
            fromfile=path,
            tofile=path,
        )
    )
    added = sum(1 for line in diff if line.startswith("+") and not line.startswith("+++"))
    removed = sum(1 for line in diff if line.startswith("-") and not line.startswith("---"))
    body = "".join(diff).rstrip("\n")
    return f"+{added} -{removed}\n{body}"
