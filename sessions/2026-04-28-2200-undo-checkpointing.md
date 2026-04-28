# 2026-04-28 22:00 UTC — /undo and edit checkpointing

**Phase:** P6 — /undo and edit checkpointing
**Status:** landed

## Summary

`write` and `edit` are the only file-mutating tools, and until now their
effects were irreversible from inside the REPL. This session adds a
process-wide pre-image stack: before either tool runs, the current bytes
of the target file are snapshotted; if the tool succeeds, the snapshot
is pushed onto the stack. A new `/undo` slash command pops the latest
entry and restores the file — overwriting it with the saved bytes, or
deleting it if the file didn't exist before. `/clear` empties the stack
alongside its existing reset of messages and usage.

The stack is in-memory only. Persisting checkpoints across REPL
restarts is intentionally out of scope; the stack is a tactical "oh
wait" affordance, not a long-term audit trail.

## Changes

- `daemon/core/checkpoints.py` — new module. `snapshot(path)` reads
  current bytes (or returns `(None, False)` for a missing file).
  `push(path, tool, content)` records an entry. `undo()` pops and
  restores — writes the saved bytes back, or `os.unlink`s the file if
  the snapshot was None. `clear()` and `count()` round out the API.
  Mirrors the module-state shape of `daemon/core/usage.py`.
- `daemon/cli/main.py` — `_run_turn` now snapshots before `write` /
  `edit` (via the new `_maybe_snapshot` helper) and pushes the
  pre-image onto the stack only when the tool result doesn't start
  with `error`. Failed tools therefore don't pollute the undo stack.
  Non-mutating tools, malformed args (non-string `path`), and snapshot
  errors all skip silently.
- `daemon/cli/commands.py` — new `/undo` command. Reports either
  `restored (pre-write)` / `restored (pre-edit)` for in-place rollback
  or `deleted (file did not exist before write)` for new-file undo,
  plus a `(N more)` hint when the stack still has entries. `/clear`
  also calls `checkpoints.clear()`.
- `daemon/tests/test_checkpoints.py` — new file, 12 tests covering:
  snapshot of present/missing files, LIFO ordering across two files,
  undo restoring bytes, undo deleting a created file, undo on an empty
  stack, undo when the "didn't exist" target is still missing,
  `clear()` semantics, and the `/undo` and `/clear` command surfaces.

- `ROADMAP.md` — moved P6 to **Done**. Removed the "/undo" item from
  **Later**. Refreshed the **Diff display** entry to point at the new
  pre-image plumbing as the natural input.

## Quality gate

```
tests:     ok       (79 passed; +12 from baseline 67)
format:    ok       (36 files already formatted)
lint:      0 errors (baseline: 0)
typecheck: 0 errors (baseline: 0)
```

## State of the application

After any `write` or `edit` tool call, `/undo` will roll the file back
— typing `/undo` repeatedly walks back through every mutation made in
the current REPL session, in reverse order. `/help` lists the new
command. `/clear` resets the undo stack along with the conversation.

Behaviour is unchanged for read-only tools (`read`, `grep`, `glob`,
`bash`, `task`): no snapshot is taken, no stack entry is added.

The pre-image bytes are kept in memory, so a long REPL with many large
writes does grow the heap. In practice this is bounded by the user's
patience for typing `/undo` and by `/clear` resetting it on every new
conversation. If it ever matters, swap the in-memory list for a small
on-disk spool.

## Suggested next steps

1. **Diff display.** Surface `difflib.unified_diff(pre_image,
   post_image)` instead of the current `"ok"` for `write`/`edit`. The
   pre-image is already captured before the tool runs in
   `_run_turn` — read the file once after the tool succeeds and feed
   both halves to difflib. Keep the current preview for non-mutating
   tools.
2. **Tests for `cli/`, `core/`, and `safety/`.** The remaining gap is
   `safety/` — `danger.py` has a few edge cases (sudo, redirected
   output, command substitution) worth pinning down. `cli/configure.py`
   round-trip tests are also still missing.
3. **Logging / debug mode.** A `--debug` flag (or `DAEMON_DEBUG=1`)
   that tees every API request/response to a file. The `call_api`
   surface is small enough to wrap cleanly.
4. **Web fetch tool.** `fetch <url>` returning text with a size cap.
   Pairs well with the existing tool-registration pattern.

## Open questions / risks

- The undo stack is per-process and per-REPL. Quitting the REPL
  forgets every checkpoint. That feels right for now (snapshots can
  be large, and the user can always `git diff`), but if someone wants
  cross-restart undo we'd need to spool to disk — likely under
  `<config_dir>/projects/<encoded-cwd>/<session-id>.undo/`.
- `_maybe_snapshot` swallows `OSError` so a permission-denied file
  doesn't block the tool dispatch (the tool itself will report the
  error). The downside: if the read fails but the write succeeds
  somehow (different file modes, ACL quirks), there's no undo entry.
  Acceptable for a v1.
- If the file is mutated externally between tool-call and `/undo`,
  `/undo` will silently overwrite the external change with the saved
  pre-image. Documenting this as expected behaviour — `/undo` is
  "restore what daemon last saw," not a 3-way merge.
