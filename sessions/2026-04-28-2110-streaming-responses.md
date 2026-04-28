# 2026-04-28 21:10 UTC — Streaming responses (P2)

**Phase:** P2 — Streaming responses
**Status:** landed

## Summary

Assistant tokens now stream to the terminal as they arrive instead of
appearing in one block at the end of each turn. `core/api.py` learned a
`stream=True` mode that sets `stream: true` and `stream_options:
{include_usage: true}` on the request, parses the OpenAI SSE feed
line-by-line, and assembles a final response dict that has the same shape
as the non-streaming reply — so `usage.add_response`,
`session.sync(messages)`, and `_assistant_message(...)` keep working
unchanged. The non-streaming path is preserved for tests and for adapters
that don't speak SSE.

The REPL turn loop opts in via a small `on_content_delta` callback that
prints the `⏺` prefix on the first delta and writes raw text deltas
directly to stdout with `flush=True`. Tool-call argument fragments are
joined by `index` and only acted on once the message is complete (they
can't be partially applied). Reasoning passthrough is preserved:
`reasoning_content` is concatenated as it streams; `reasoning` and
`reasoning_details` (provider-specific shapes) take last-write-wins.

## Changes

- `daemon/core/api.py` — `call_api()` gained keyword-only `stream` and
  `on_content_delta` parameters. New private `_accumulate_stream()` reads
  bytes lines from the response, skips comments / blanks / malformed
  JSON, and folds content, tool calls, reasoning fields, and the trailing
  usage block into a `{"choices": [{"message": ...}], "usage": ...}`
  dict that's indistinguishable from the non-streaming response.
- `daemon/cli/main.py` — `_run_turn()` now requests streaming. A nested
  `on_delta` prints `\n⏺ ` on the first delta and raw text after that;
  once the stream finishes we emit the trailing newline and proceed with
  tool-call dispatch as before. The buffered `render_markdown(...)` path
  is kept as a fallback for adapters that don't actually stream content.
- `daemon/tests/test_api.py` — new file. Covers the non-streaming
  contract, content-delta assembly + callback fan-out, tool-call
  reassembly across chunks, multiple indexed tool calls in a single
  delta, usage-chunk capture, `reasoning_content` concatenation,
  tolerance for blank / comment / malformed lines, and request-body
  flag-shape (with vs. without `stream=True`).
- `ROADMAP.md` — moved P2 to Done; "Now" is empty pending the next pick.

## Quality gate

```
tests:     ok       (67 passed; +9 from baseline 58)
format:    ok       (34 files already formatted)
lint:      0 errors (baseline: 0)
typecheck: 0 errors (baseline: 0)
```

## State of the application

Run `daemon`, ask a question, and the answer types itself out in real
time. Tool calls still print as a block (the `⏺ Toolname(arg)` line is
still emitted only after the model completes a tool-bearing message,
since arguments arrive in fragments and we can't dispatch a partial
call). `--continue`, `--resume`, `/rewind`, `/sessions`, `/usage`, and
the rest of the slash registry are unchanged — `usage.add_response()`
sees the same response shape it did before, so the tracker keeps
counting, and the JSONL session writer keeps appending.

The non-streaming path still works: pass nothing for `stream`, get a
single `urlopen().read()` + `json.loads`. Tests use it directly and so
can any future adapter that buffers internally.

## Suggested next steps

1. **/undo and edit checkpointing.** Top of the **Later** list and a
   well-scoped phase. Snapshot the target file before any `write` /
   `edit` tool call so `/undo` can restore it. The slash-command
   registry and `commands.set_session()` give you the hook you need;
   stash the previous bytes alongside the session and surface them via
   a new `/undo` command.
2. **Diff display.** Show a unified diff for `write` / `edit` results
   instead of the current "ok". Pairs nicely with #1 (the captured
   pre-image is exactly what `difflib.unified_diff` wants).
3. **Markdown re-render after stream.** Today bold (`**foo**`) is
   rendered for non-streamed content but not for streamed content,
   because we can't rewrite already-printed bytes safely across
   terminals. If we ever want it back, the cleanest approach is to
   buffer one paragraph at a time and emit on `\n\n`. Skip until
   someone asks.
4. **Tests for `cli/`, `core/`, and `safety/`.** Coverage is improving
   (`tests/test_api.py`, `tests/test_sessions.py`, `tests/test_usage.py`,
   `tests/test_commands.py` all exist now). The next gap is `safety/` —
   a few danger-pattern edge cases would shore it up.

## Open questions / risks

- Mid-stream content is printed raw, so `**bold**` markers appear as
  literal asterisks in streamed assistant turns. The non-streaming
  fallback in `_run_turn` still calls `render_markdown`, so adapters
  that don't actually stream still get bold. Acceptable trade-off for
  the streaming UX win; documented in "Suggested next steps."
- `_accumulate_stream` consumes the response by iterating it as bytes
  lines (Python's `HTTPResponse` is line-iterable). If a backend ever
  returns SSE without trailing newlines, the loop would block until
  the connection closes. No real-world OpenAI-compatible server does
  this today, so leaving it.
- `stream_options: {include_usage: true}` is OpenAI-specific. If a
  given adapter ignores it, we still get the assembled message; we
  just lose the per-turn usage tally for streamed turns. The tracker
  silently absorbs the missing block, so nothing breaks.
