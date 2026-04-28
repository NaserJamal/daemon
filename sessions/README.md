# sessions/

Breadcrumb log. One file per agent session — small, dated, and append-only.

The next agent starts by reading the **most recent file here**, then
`ROADMAP.md`, then `AGENTS.md`. Don't edit older breadcrumbs; write a new
one.

## Naming

```
sessions/YYYY-MM-DD-HHMM-<short-slug>.md
```

Use UTC. The slug should match the phase ID or describe the change in 1–4
words: `2026-05-01-0930-streaming.md`, `2026-05-01-1730-p1-lint.md`.

## Writing one

Copy `TEMPLATE.md`, fill it in, keep it short. The point is to give the next
agent enough context to pick up cold — not to exhaustively document the
diff. The git log already does that.

A good breadcrumb:

- States which phase was tackled and whether it landed.
- Records the quality-gate output (pass / fail counts), so regressions are
  obvious.
- Names 1–3 concrete next steps. Vague advice like "improve the code" is
  not useful.
