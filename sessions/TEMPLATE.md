# <YYYY-MM-DD HH:MM UTC> — <short title>

**Phase:** <e.g. P2 — Streaming responses, or "ad-hoc: fix grep regression">
**Status:** <landed | partial | blocked>

## Summary

One paragraph. What you set out to do, what actually changed, and why.

## Changes

- `path/to/file.py` — what changed and why.
- `path/to/other.py` — what changed and why.

## Quality gate

Output of `./scripts/check.sh` (paste the summary lines, not the full log):

```
tests:     <N passed, M failed>
format:    <ok | N files reformatted>
lint:      <N errors>      (baseline before this session: <N>)
typecheck: <N errors>      (baseline before this session: <N>)
```

## State of the application

What works now that didn't before. Anything new the next agent should know
about (new commands, new env vars, new files in unusual places).

## Suggested next steps

1. <Concrete, named phase or task>
2. <…>
3. <…>

## Open questions / risks

Anything the next agent should think about before diving in. Delete this
section if there's nothing to flag.
