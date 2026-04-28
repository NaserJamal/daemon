# 2026-04-28 15:47 UTC — Slash-command registry & /help (P3)

**Phase:** P3 — `/help` and slash-command discoverability
**Status:** landed

## Summary

Replaced the chained-`if` dispatcher in `daemon/cli/commands.py` with a
small decorator-based registry, then re-registered the four built-ins
(`/help`, `/clear`, `/config`, `/quit`) on top of it. Added `/help`,
which prints every registered command's name, description, and aliases.
Unknown `/foo`-style input is now caught and reported instead of being
forwarded to the model. The `cli/main.py` integration point is
unchanged — it still calls `commands.handle(user_input, messages)` and
gets the same `False | True | None` contract back.

## Changes

- `daemon/cli/commands.py` — full rewrite. New `Command` dataclass and
  `register_command(name, description, *, aliases=())` decorator;
  `_DISPATCH` maps every alias to its `Command`; `handle()` looks up
  the head token, dispatches, and treats unknown `/...` heads as
  "handled" with a friendly error so they don't leak to the model.
  `commands()` returns the primary commands sorted for `/help` to
  iterate. Each built-in is a tiny private function decorated at
  module load.
- `daemon/tests/test_commands.py` — new file. Nine tests covering
  registry presence, alias dispatch (`/q`, `/exit`, `exit` all quit),
  `/help` listing every registered command and its description,
  `/clear` resetting messages (including via the `/c` alias), unknown
  `/nope` input being handled with a printed warning, and plain text /
  whitespace falling through to the model (returning `None`).
- `ROADMAP.md` — moved P3 to Done with this breadcrumb's filename.

## Quality gate

```
tests:     ok       (27 passed; +9 from baseline 18)
format:    ok       (29 files already formatted)
lint:      0 errors (baseline: 0)
typecheck: 0 errors (baseline: 0)
```

## State of the application

`/help`, `/h`, and `/?` now print the full slash-command catalogue.
`/quit`, `/q`, `/exit`, and bare `exit` still quit. `/clear` and `/c`
still reset history. `/config` and `/configure` still launch the
configure flow. Mistyped slash commands (e.g. `/quitt`) print
`Unknown command: /quitt (try /help)` instead of being sent to the
model — that's a behaviour change worth flagging, but it's the more
useful default.

Adding a new slash command is now mechanical and matches the shape
described in `daemon/CONTRIBUTING.md`:

```python
@register_command("/foo", "what /foo does", aliases=("/f",))
def _cmd_foo(args: list[str], messages: list[dict[str, Any]]) -> bool | None:
    ...
    return True
```

The handler signature differs slightly from `CONTRIBUTING.md`'s example
(it takes `messages` directly rather than a `repl` object) — there's no
`repl` object today and the only built-in that needs state is `/clear`,
so introducing one would be a premature abstraction. If a future
command needs broader REPL access, promote the second argument to a
context object then.

## Suggested next steps

1. **P2 — Streaming responses.** Still the biggest UX win. `core/api.py`
   is small; add a `stream_api()` alongside `call_api()` that yields
   content deltas and buffers tool-call deltas until the message
   completes, then teach `cli/main.py:_run_turn` to render the stream.
   Keep `call_api()` for tests.
2. **P4 — Cost & token tracking.** Now trivial to wire up as a `/usage`
   slash command using the new registry — the handler can read a
   running counter that `_run_turn` updates from each response's
   `usage` block.
3. **Tests for `cli/`, `core/`, `safety/`** (still in Later). This
   session covered `cli/commands.py`; `cli/io.py` (`render_markdown`,
   `separator`) and `core/user_config` (round-trip) are the next
   easiest wins.

## Open questions / risks

The unknown-slash-command behaviour change (catch `/foo` instead of
forwarding it) is a small but real shift. It's tested, documented
here, and matches what a user would expect — but if a future feature
wants `/`-prefixed input to reach the model (e.g. literal Markdown
fenced into a prompt), the rule will need to be relaxed.
