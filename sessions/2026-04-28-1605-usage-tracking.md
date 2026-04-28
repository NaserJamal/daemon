# 2026-04-28 16:05 UTC — Token usage tracking & /usage command (P4)

**Phase:** P4 — Cost & token tracking
**Status:** landed

## Summary

Added a process-wide token-usage tracker and a `/usage` slash command.
Each chat-completion response feeds its `usage` block into a singleton
`Usage` accumulator, so users can read running input/output totals at any
point. `/usage` prints the current totals and accepts `on`/`off` to toggle
a compact per-turn summary line that the REPL prints after each assistant
turn. `/clear` now also zeroes the usage counters along with the message
history. Cost reporting was scoped out — the API responses we target
don't carry pricing, and pricing-by-model would mean either a hardcoded
table or a new config knob, neither of which earns its keep yet.

## Changes

- `daemon/core/usage.py` — new module. A frozen `Usage` dataclass plus
  module-level singleton, with `current()`, `reset()`, `add_response()`,
  `set_show_per_turn()`/`show_per_turn()`, and `format_summary()`.
  Malformed/missing `usage` blocks are coerced safely so a server that
  omits them never crashes the REPL.
- `daemon/cli/main.py` — `_run_turn` now feeds every response into
  `usage.add_response()`. The REPL loop prints
  `usage: N requests | in: ... | out: ... | total: ...` after each user
  turn when per-turn display is enabled.
- `daemon/cli/commands.py` — registered `/usage` (alias `/u`). With no
  args it prints the running summary plus the per-turn state; with `on`
  or `off` it toggles per-turn display. `/clear` now also calls
  `usage.reset()`.
- `daemon/tests/test_usage.py` — new file. Twelve tests covering empty
  state, accumulation across multiple responses, malformed-payload
  handling, reset, summary formatting, the `/usage` command (including
  the `/u` alias, `on`/`off` toggle, invalid arg, and reset-on-`/clear`).
- `ROADMAP.md` — moved P4 to Done.

## Quality gate

```
tests:     ok       (39 passed; +12 from baseline 27)
format:    ok       (31 files already formatted)
lint:      0 errors (baseline: 0)
typecheck: 0 errors (baseline: 0)
```

## State of the application

`/usage` shows running token totals; `/usage on` enables a compact
post-turn summary; `/usage off` disables it (the default). `/clear`
now resets both the message list and the usage tracker, which matches
how a user thinks about "starting over."

The tracker lives in module state in `daemon/core/usage.py`. The earlier
breadcrumb anticipated promoting the slash-command handler signature to
take a context object once a command needed broader REPL state — a
singleton turned out to be a smaller, equally clean fit here, since
`_run_turn` and the slash command both need to read/write the same
counter and there's no per-conversation isolation to worry about. Revisit
the context-object refactor only if a future command needs *true*
per-REPL state (e.g. multiple concurrent sessions).

## Suggested next steps

1. **P2 — Streaming responses.** Still the biggest UX win and still
   untouched. The hook point is now even cleaner: `_run_turn` already
   calls `usage.add_response(response)` on the full payload, so a
   streaming variant just needs to assemble the final response (or a
   final `usage` block) before that call.
2. **P5 — Conversation persistence.** `/save <name>` and `/load <name>`
   into `<config_dir>/sessions/`. Use `json` (not `pickle`) and treat
   files as untrusted on read.
3. **Cost display.** If you want true cost numbers, the cleanest path is
   a small `MODEL_PRICES` table in `core/usage.py` keyed by
   `settings.model_name`, with a `cost_usd` field on `Usage` updated in
   `add_response()`. Skip it until a user actually asks for it — the
   table will rot.
4. **Tests for `cli/io.py` and `core/user_config`** (still in Later).

## Open questions / risks

The per-turn display defaults to **off**. That keeps the REPL output
clean for first-time users but means the feature is invisible until
someone runs `/usage`. `/help` lists it, so discoverability is fine, but
if you'd rather have it on by default flip the initial value of
`_show_per_turn` in `daemon/core/usage.py`.
