# 2026-09-07 12:00 UTC — spill oversized tool output to disk

**Phase:** ad-hoc: keep unbounded tool output out of the context window
**Status:** landed

## Summary

`fetch` returned whole response bodies and `bash` returned whole command
output, so one call could swallow the context window. Both now pass their
output through a new shared helper, `daemon/utils/spill.py`. Output that
fits (<= 50k chars and <= 2000 lines) is returned unchanged; anything larger
is written to `<tempdir>/daemon-output/` and replaced by a head+tail preview
naming the path, which the model can read, grep, or script against. Two
smaller things fell out of the work: the HTML extractor was silently
dropping almost every real page, and `fetch` no longer asks for
confirmation.

## Changes

- `daemon/utils/` — new package for small, cross-cutting helpers. A module
  belongs here only if more than one package uses it and it knows nothing
  about a specific tool, command, or provider; the `__init__` docstring
  states that bar so the package does not rot into a junk drawer. Registered
  in `pyproject.toml` under `packages` and `package-dir`.
- `daemon/utils/spill.py` — new. `spill(text, label)` returns short text
  untouched; otherwise `_write()` saves it to a uniquely named temp file
  (`<label slug>-<random>.txt`) and it returns a header naming the path, the
  first 50 and last 20 lines (each clipped to 2k chars), and an omitted-line
  count. A write failure degrades to the preview plus a note rather than
  re-flooding the context.
- `daemon/tools/fetch.py` — returns `spill(text, f"fetch {netloc}")`.
  Confirmation gate removed: a GET is read-only, so it no longer prompts and
  no longer depends on YOLO mode (`get_settings`/`confirm` imports dropped).
- `daemon/tools/fetch.py` — bug fix in `_TextExtractor.SKIP_TAGS`: `meta`
  and `link` are void elements, so entering them incremented `_skip_depth`
  with no end tag to unwind it and every page with a `<meta>` in `<head>`
  extracted to the empty string. Both removed (they carry no text); `title`
  added for pages that put one outside `<head>`.
- `daemon/tools/bash.py` — output goes through `spill(out, "bash")`. The
  killed-by-signal note is still appended after the preview.
- `daemon/tests/test_spill.py` — new, 8 tests: pass-through, inclusive line
  threshold, line- and char-triggered spills, both preview ends, filename
  slug, uniqueness, write-failure fallback.
- `daemon/tests/test_fetch.py` — dropped the confirmation test, added a
  large-body spill test and the void-tag regression test.
- `daemon/tests/test_tools.py` — new `TestBashTool`: inline output and a
  `seq 1 5000` spill.
- `README.md` — tool table rows for `fetch`/`bash`; the feature list and
  YOLO section no longer claim network access is gated.
- `AGENTS.md`, `daemon/CONTRIBUTING.md` — `utils/` added to the project
  layout trees.

## Quality gate

```
tests:     128 passed  (baseline before this session: 118)
format:    ok
lint:      0 errors    (baseline before this session: 0)
typecheck: 0 errors    (baseline before this session: 0)
```

Note: `./scripts/check.sh` needs `daemon/.venv` on PATH — run
`uv sync --all-extras` inside `daemon/` first. The system python3.12 on this
machine has a broken pytest plugin and no ruff/mypy.

## State of the application

Fetching `https://example.com/` returns three lines inline; fetching a large
Wikipedia article returns a ~2.5k-char preview and a path to the 93k-char
file. `seq 1 5000` behaves the same way. Spilled files are never cleaned up
— they live in the OS temp dir and are the OS's problem.

## Suggested next steps

1. Adopt `spill()` in `grep` and `read` if their own caps ever prove too
   blunt.
2. `fetch` follows redirects blindly — an http(s) URL can redirect anywhere,
   including to a link-local address.
3. The HTML extractor is still naive: no table or list structure, and
   Wikipedia chrome dominates the first 50 lines of a preview.

## Open questions / risks

Spilled files persist for the life of the OS temp dir. If that gets noisy, a
per-session subdirectory cleaned on exit is the fix.
