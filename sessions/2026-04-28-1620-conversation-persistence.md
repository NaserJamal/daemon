# 2026-04-28 16:20 UTC — Conversation persistence (P5)

**Phase:** P5 — Conversation persistence
**Status:** landed

## Summary

Conversations are now auto-saved to disk per project. The layout mirrors
Claude Code's: each working directory gets its own folder under
`<config_dir>/projects/<encoded-cwd>/`, and every session inside is a
JSON-Lines transcript appended to as messages flow. `daemon --resume`
shows a numbered list of recent sessions for the current cwd and lets
the user pick one; `daemon --continue` jumps straight into the most
recent session. There's no `/save` command — saving is the default,
silent behaviour.

A new `/rewind` slash command rolls the conversation back to before a
chosen user message and rewrites the transcript to match. Double-tapping
**Escape** in the prompt clears whatever the user has typed so far,
matching the request from the handoff.

JSON (one event per line) was chosen over SQLite. The volume is tiny
(one process, append-only, no concurrent writers), JSONL is trivially
diffable / `cat`-able / `jq`-able, and the read path is `json.loads` per
line — no extra dependency, no schema migrations, no `pickle` (the
ROADMAP explicitly called out treating files as untrusted on read).

## Changes

- `daemon/core/sessions.py` — new module. `Session.new()` creates a file
  and writes a `{"type":"meta", "cwd":..., "created_at":...}` header;
  `Session.sync(messages)` appends only un-persisted messages on each
  call; `Session.rewrite(messages)` does an atomic temp-file + rename
  for `/rewind`; `Session.open(path)` replays a transcript. Module-level
  `list_sessions(cwd)` / `latest_session(cwd)` / `format_age(...)` /
  `encode_cwd(...)` round out the picker's needs. Corrupt or non-`dict`
  lines are skipped on read so a half-written line never bricks resume.
- `daemon/cli/main.py` — REPL now creates (or resumes) a `Session` at
  startup and calls `session.sync(messages)` after every turn and after
  any slash command that mutates history. New helpers
  `_pick_session()` (the `--resume` numbered prompt) and
  `_start_session(argv)` keep the entry-point readable. `--resume` /
  `-r` and `--continue` / `-c` are stripped from argv before
  `handle_subcommand` so they aren't mistaken for unknown subcommands.
- `daemon/cli/commands.py` — added `set_session()` / `get_session()` so
  the REPL and slash commands share a single active session. `/clear`
  now starts a fresh session (the prior transcript is preserved on
  disk, like Claude Code). New `/rewind [N]` truncates `messages` to
  before the chosen user message and `rewrite()`s the file. New
  `/sessions` lists recent transcripts for the current directory and
  marks the active one.
- `daemon/cli/prompt.py` — bound `escape, escape` to clear the input
  buffer. `escape, enter` (Alt+Enter newline) still works because
  prompt_toolkit disambiguates by chord.
- `daemon/tests/test_sessions.py` — new file. Round-trip, append-only
  sync, atomic rewrite, corrupt-line tolerance, per-cwd isolation, age
  formatter, `/rewind` happy-path / no-user-msgs / out-of-range, and
  `/clear` swap-to-new-session.
- `ROADMAP.md` — moved P5 to Done.

## Quality gate

```
tests:     ok       (58 passed; +19 from baseline 39)
format:    ok       (33 files already formatted)
lint:      0 errors (baseline: 0)
typecheck: 0 errors (baseline: 0)
```

## State of the application

Everything saves itself. Run `daemon` and your conversation lands at
`~/.config/daemon/projects/<encoded-cwd>/<id>.jsonl` (or the macOS /
Windows equivalents). Run `daemon --resume` to pick an old conversation
for the current directory; run `daemon --continue` to skip the picker
and grab the most recent one.

`/rewind` opens an interactive picker of user messages; `/rewind 3`
skips it. The chosen user message and everything after it are dropped
from both memory and disk. `/sessions` lists what's saved for this cwd.

Double-Escape in the REPL prompt clears the buffer.

## Suggested next steps

1. **P2 — Streaming responses.** Still unstarted and still the biggest
   visible UX win. The `_run_turn` hook is unchanged; assemble the final
   `usage` block before `usage.add_response(response)` and
   `session.sync(messages)` and the persistence layer "just works."
2. **Resume picker polish.** Today `--resume` uses plain `input()`. Now
   that prompt_toolkit is already a dependency, an arrow-key picker
   would be a small follow-up. Out of scope for this phase.
3. **`/branch` (or fork-from-rewind).** `/rewind` discards the rewound
   tail. A future `/rewind --branch N` could copy the file first and
   start a new session with the truncated prefix, so the old timeline
   is recoverable. Skip until someone asks.
4. **Auto-titles.** The picker currently labels each session by its
   first user message. A periodic background "name this session" call
   would be nicer but earns its keep only at higher volume.
5. **Pruning.** Sessions never expire. A `daemon sessions prune
   --older-than 30d` subcommand is a five-minute add when the directory
   gets noisy.

## Open questions / risks

- `encode_cwd` is one-way: `/home/x` and `/home-x` collide. The original
  cwd is preserved inside each session's `meta` header, so display is
  fine, but two distinct directories that encode to the same folder
  name would share a transcript pool. Acceptable today; revisit if it
  bites.
- `sync()` does a `with open(..., "a")` per turn. Cheap, but if turns
  ever fan out (parallel subagents writing into the same transcript),
  we'd want a single open file handle plus a lock. Not needed yet.
- `--resume` and `--continue` are silently ignored when followed by a
  subcommand like `daemon configure` (they're stripped before dispatch).
  That's the right call — those flags only mean something for the REPL —
  but worth knowing if a future subcommand ever wants to honour them.
