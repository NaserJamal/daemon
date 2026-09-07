# AGENTS.md

This is the canonical guide for any agent (or human) making incremental
improvements to `daemon`. Read it in full before touching code.

## Workflow

This repo is built to be improved one phase at a time via the **handoff
prompt** (see `README.md`). Every session follows the same shape:

1. **Read context.** Read the latest breadcrumb in `sessions/` and skim
   `ROADMAP.md`. Skim the modules you intend to touch.
2. **Pick one phase.** Pick a single phase from `ROADMAP.md` (or a smaller,
   well-scoped task discovered while reading the code). One phase per session.
3. **Build it.** Make the change. Add tests for new behaviour.
4. **Verify.** Run `./scripts/check.sh`. Do not finish a session with a
   regression — see "Quality bar" below.
5. **Hand off.** Write a new breadcrumb to `sessions/` using
   `sessions/TEMPLATE.md`. Move the phase to "Done" in `ROADMAP.md` if you
   completed it; add follow-ups discovered along the way.

## Quality bar

The repo's quality must not regress. Before finishing a session:

- `./scripts/check.sh` runs and the `tests` and `format` sections are clean.
- The `lint` and `typecheck` sections must not have *more* errors than the
  baseline recorded in the latest breadcrumb. Prefer to leave them better.
- Any new behaviour has at least one test in `daemon/tests/`.
- `python -m daemon --help` (or equivalent) still works — don't break the
  entry point.

If you can't meet the bar, stop and write a breadcrumb explaining what's
blocking — don't paper over a failure.

## Code style

`daemon`'s value is being a *minimal*, readable harness. Every change should
preserve that.

- **Type hints everywhere.** New code is fully typed. `from __future__ import
  annotations` at the top of every module.
- **Docstrings on public functions and classes.** One line is usually enough;
  add a longer block only when the *why* is non-obvious.
- **No comments that just restate the code.** Only write a comment when it
  explains *why* — a hidden constraint, an invariant, or a workaround.
- **Small, focused functions.** If a function grows past ~40 lines, ask if it
  wants to be two functions.
- **No premature abstractions.** Three similar lines is fine; a config-driven
  framework for two call sites is not. Don't build for hypothetical futures.
- **No dead code or compatibility shims.** If you remove something, remove its
  callers too. Don't leave `# kept for backwards compat` comments unless an
  external consumer truly relies on it.
- **Errors, not exceptions, at tool boundaries.** Tool `execute()` methods
  return error *strings*; they do not raise.
- **No emoji** in code or commits unless the user asked for one.

## Project layout

```
daemon/                 # Python package (installed as `daemon`)
├── __init__.py         # public API surface
├── __main__.py         # `python -m daemon`
├── cli/                # REPL, prompt, slash commands, configure flow
├── core/               # api client, settings, system prompt, user config
├── safety/             # danger-pattern detection, confirmation prompts
├── tools/              # tool implementations + registry
├── utils/              # small cross-cutting helpers (see its docstring)
└── tests/              # pytest suite

sessions/               # breadcrumbs (handoff log; one file per session)
ROADMAP.md              # phased work queue
scripts/check.sh        # tests + lint + format-check + typecheck
```

The package lives under `daemon/` (a sub-directory of the repo root) for
historical reasons. `pyproject.toml` and `pip install -e ./daemon` live there
too. Run all `pytest` / `ruff` / `mypy` from the repo root via
`./scripts/check.sh`, which `cd`s into the right place.

## Adding a tool

`daemon/CONTRIBUTING.md` has the full guide. The short version:

1. Create `daemon/tools/<name>.py` with a `BaseTool` subclass decorated with
   `@register_tool`.
2. Import it from `daemon/tools/__init__.py`.
3. Add a test in `daemon/tests/test_tools.py`.

Tools must return strings (including for errors) and must not raise.

## Adding a slash command

See `daemon/cli/commands.py` and `daemon/CONTRIBUTING.md`. Slash commands
return `False` to quit, `True` if handled, or `None` to fall through to the
model.

## Things to avoid

- Adding a new third-party dependency without a strong reason. The project's
  pitch is "few dependencies"; treat each one as a tax on every future user.
- Renaming public API in `daemon/__init__.py` without updating callers and
  tests in the same change.
- Long-lived feature flags or config knobs for one-off behaviour.
- Reformatting unrelated files alongside a feature change. Keep diffs
  reviewable.

## When in doubt

Ship the smallest change that makes the next thing easier. Leave a note in
the breadcrumb so the next agent knows what you saw.
