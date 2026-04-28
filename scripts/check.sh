#!/usr/bin/env bash
#
# Quality gate. Runs from anywhere; cd's to the repo root, then into the
# package directory for ruff / mypy. Prints a one-line summary per stage and
# exits non-zero if tests or formatting fail.
#
# Lint and typecheck errors are reported but don't fail the script — they're
# tracked against a baseline in the latest sessions/ breadcrumb. The agent's
# job is to not let those numbers grow.

set -u
cd "$(dirname "$0")/.." || exit 2

PKG=daemon
fail=0

heading() { printf '\n=== %s ===\n' "$1"; }

heading "tests"
if python -m pytest "$PKG/tests" -q; then
    tests_status="ok"
else
    tests_status="FAILED"
    fail=1
fi

heading "format (ruff format --check)"
if (cd "$PKG" && python -m ruff format --check .); then
    format_status="ok"
else
    format_status="FAILED — run 'python -m ruff format daemon/' to fix"
    fail=1
fi

heading "lint (ruff check)"
lint_output=$(cd "$PKG" && python -m ruff check . 2>&1) || true
echo "$lint_output"
lint_count=$(echo "$lint_output" | grep -Eo 'Found [0-9]+ error' | grep -Eo '[0-9]+' | head -1)
lint_count=${lint_count:-0}

heading "typecheck (mypy)"
type_output=$(cd "$PKG" && python -m mypy . 2>&1) || true
echo "$type_output"
type_count=$(echo "$type_output" | grep -Eo 'Found [0-9]+ error' | grep -Eo '[0-9]+' | head -1)
type_count=${type_count:-0}

heading "summary"
printf 'tests:     %s\n'   "$tests_status"
printf 'format:    %s\n'   "$format_status"
printf 'lint:      %s errors\n' "$lint_count"
printf 'typecheck: %s errors\n' "$type_count"

exit "$fail"
