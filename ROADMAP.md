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

_(Empty — pick one from **Later** below, or open a new phase.)_

---

## Later

- **Tests for `cli/`, `core/`, and `safety/`.** Today only `tools/` has
  coverage. Aim for the easy wins: command handler, danger detector edges,
  config round-trip.
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
- P2 — Streaming responses — sessions/2026-04-28-2110-streaming-responses.md
- P6 — /undo and edit checkpointing — sessions/2026-04-28-2200-undo-checkpointing.md
- P7 — Diff display for write/edit — sessions/2026-04-30-1817-diff-display.md
- P8 — Debug-mode API logging — sessions/2026-05-06-1200-debug-mode.md
