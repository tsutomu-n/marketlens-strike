<!--
作成日: 2026-06-26_19:22 JST
更新日: 2026-06-26_19:22 JST
-->

# Pass 390: Paper Cycle History Note Helpers

## Purpose

Reduce `src/sis/reports/paper_cycle_history.py` by extracting note value and note count parsing into a focused helper module.

## Restart Basis

- Branch: `refactor/backtest-primitives`
- HEAD: `30e43d1`
- Preserve: Pass 377 through Pass 389 uncommitted changes.
- Latest broad verification before this pass: Pass 389 `./scripts/check` passed with `2698 passed in 79.49s`.

## Target Files

- `src/sis/reports/paper_cycle_history.py`
- `src/sis/reports/paper_cycle_history_notes.py`
- `tests/test_paper_cycle_history_notes.py`

## Scope

- Move note prefix parsing and per-note count aggregation into `paper_cycle_history_notes.py`.
- Keep the report builder, summary key names, Markdown text/order, navigation helpers, and CLI behavior unchanged.
- Remove no runtime artifacts and introduce no dependencies.

## Out Of Scope

- Public CLI names/options.
- Summary key names or artifact key names.
- Markdown/report wording or ordering.
- Navigation map changes.
- Schema, auth, DB, CI, dependencies, paper/live safety boundaries.

## Red-Green-Refactor

1. RED: Add direct tests for the new note helper module.
2. GREEN: Move only note parsing helpers and update imports.
3. REFACTOR: Run focused note tests, existing paper cycle history tests, CLI smoke, lint/type/CLI checks, `git diff --check`, and `./scripts/check`.

## Verification Plan

- `CI=true timeout 120 uv run pytest -q tests/test_paper_cycle_history_notes.py`
- `CI=true timeout 120 uv run pytest -q tests/test_paper_cycle_history_notes.py tests/test_paper_cycle_history_navigation.py`
- `CI=true timeout 120 uv run pytest -q tests/test_monitoring_comparison.py -k 'paper_cycle_history'`
- `CI=true timeout 120 uv run pytest -q tests/test_cli_smoke.py -k 'paper_cycle_history'`
- `uv run ruff format src/sis/reports/paper_cycle_history.py src/sis/reports/paper_cycle_history_notes.py tests/test_paper_cycle_history_notes.py`
- `uv run ruff check src/sis/reports/paper_cycle_history.py src/sis/reports/paper_cycle_history_notes.py tests/test_paper_cycle_history_notes.py`
- `uv run ty check src --python-version 3.13 --output-format concise`
- `uv run sis --help | wc -l`
- `git diff --check`
- `./scripts/check`

## Practical Review

- Best next target: `paper_cycle_history.py` remains a large report module and has a small pure parsing subset.
- Safer boundary: note parsing does not write files or define report text; existing integration tests lock the report output.
- Main risk: changing how non-list or non-dict note payloads are ignored. Mitigation: direct tests include malformed rows.
- Stop condition: if extracting notes changes summary keys or Markdown output, revert to a smaller boundary.

## Branch Decision

Continue on `refactor/backtest-primitives`. This is the existing dedicated refactor branch, and this pass is a small behavior-preserving split.
