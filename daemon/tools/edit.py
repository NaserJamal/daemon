"""Edit tool: substring replace with whitespace-tolerant fallback."""

from __future__ import annotations

from typing import Any

from daemon.tools.base import BaseTool
from daemon.tools.registry import register_tool


def _find_match(text: str, old: str) -> tuple[str | None, int]:
    """Locate `old` in `text`, returning (matched_substring, occurrence_count).

    Falls back to a per-line strip-compare so the model can omit exact
    leading/trailing whitespace. Returns (None, 0) when nothing matches.
    """
    if old in text:
        return old, text.count(old)

    file_lines = text.split("\n")
    old_lines = old.split("\n")
    if not old_lines or len(old_lines) > len(file_lines):
        return None, 0

    target = [line.strip() for line in old_lines]
    matches: list[str] = []
    for i in range(len(file_lines) - len(old_lines) + 1):
        window = file_lines[i : i + len(old_lines)]
        if [line.strip() for line in window] == target:
            candidate = "\n".join(window)
            if candidate in text:
                matches.append(candidate)

    if not matches:
        return None, 0
    # Prefer a candidate that occurs exactly once - that disambiguation
    # lets us replace without `all=true` even when several windows trim
    # to the same target.
    unique = [c for c in matches if text.count(c) == 1]
    chosen = unique[0] if unique else matches[0]
    return chosen, text.count(chosen)


@register_tool
class EditTool(BaseTool):
    name = "edit"
    description = (
        "Replace `old` with `new` in file. `old` must match uniquely unless all=true. "
        "Per-line leading/trailing whitespace is tolerated. If `old` is empty, the file "
        "is created/overwritten with `new`. Never include the 'N| ' line-number prefix "
        "from read() output in `old` or `new`."
    )
    parameters = {"path": "string", "old": "string", "new": "string", "all": "boolean?"}

    def execute(self, args: dict[str, Any]) -> str:
        path, old, new = args["path"], args["old"], args["new"]
        if old == new:
            return "error: old and new are identical"

        if old == "":
            with open(path, "w", encoding="utf-8") as f:
                f.write(new)
            return "ok (created)"

        with open(path, encoding="utf-8") as f:
            text = f.read()

        candidate, count = _find_match(text, old)
        if candidate is None:
            return "error: old not found in file"
        if count > 1 and not args.get("all"):
            return f"error: old matches {count} places, add more context or pass all=true"

        n = -1 if args.get("all") else 1
        with open(path, "w", encoding="utf-8") as f:
            f.write(text.replace(candidate, new, n))
        return "ok"
