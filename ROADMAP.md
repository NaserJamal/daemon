# ROADMAP

The phased work queue for `daemon`. Each phase is a self-contained chunk an
agent can complete in one session. Pick the highest-priority phase you can
finish cleanly; one phase per session.

When you finish a phase, move it from **Now** to **Done** with the
breadcrumb filename so the trail is auditable. New work discovered along
the way goes in **Later**.

> Read `AGENTS.md` first for the quality bar and code-style rules.

---

## Now (pick one)

### P2 — Streaming responses
`core/api.py` reads the whole response before printing. Stream tokens to the
terminal so the user sees progress. Keep the non-streaming path available
for tests.
- Use `stream: true` on the chat-completions request.
- Render content deltas as they arrive; buffer tool-call deltas until the
  message is complete (tool calls can't be partially applied).
- Preserve existing reasoning-field passthrough.

---

## Later

- **/undo and edit checkpointing.** Snapshot files before any `write`/`edit`
  tool call so `/undo` can restore the last-modified file.
- **Diff display.** Show a unified diff for `write` and `edit` results
  instead of the current "ok".
- **Tests for `cli/`, `core/`, and `safety/`.** Today only `tools/` has
  coverage. Aim for the easy wins: command handler, danger detector edges,
  config round-trip.
- **Logging / debug mode.** A `--debug` flag (or env var) that prints API
  requests/responses to a file.
- **Web fetch tool.** `fetch <url>` returns text, with a size cap and a
  hostname allowlist or confirmation prompt.
- **MCP client support.** Connect to MCP servers and expose their tools
  through the existing registry.
- **Subagent polish.** `tools/task.py` exists but is barely wired up — make
  it a first-class tool with its own system prompt and bounded loop.
- **Smarter context management.** When messages grow past a budget,
  summarise older turns or drop tool results.
- **Release pipeline.** GitHub Actions for tests + lint on PR; tagged
  release publishes to PyPI.
- **Dockerfile.** A minimal image that runs `daemon` against a mounted
  workspace.

---

## Done

_(Move completed phases here with a link to the breadcrumb that finished
them. Format: `- P1 — Lint & type cleanup — sessions/2026-04-29-1400-lint.md`)_

- P0 — Agent-handoff scaffolding — sessions/2026-04-28-1518-genesis.md
- P1 — Lint & type cleanup — sessions/2026-04-28-1531-lint-and-types.md
- P3 — `/help` and slash-command discoverability — sessions/2026-04-28-1547-slash-command-registry.md
- P4 — Cost & token tracking — sessions/2026-04-28-1605-usage-tracking.md
- P5 — Conversation persistence — sessions/2026-04-28-1620-conversation-persistence.md
