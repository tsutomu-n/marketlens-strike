<!--
作成日: 2026-06-26_21:28 JST
更新日: 2026-06-26_21:28 JST
-->

# Pass 403 Weekly Review Current Gate

## Purpose

Extract the Current Trade[XYZ] Gate Snapshot section line builder from `src/sis/reports/weekly_review.py` into a focused helper module.

## Scope

- Add `src/sis/reports/weekly_review_current_gate.py`.
- Move only the current phase gate snapshot section lines.
- Preserve heading text, bullet text, bullet order, backtest symbol scope wording, and blank line placement.
- Keep `build_weekly_review_report()` loading and report assembly behavior unchanged.
- Add direct tests for populated, missing, and historical/backtest symbol scope cases.

## Out Of Scope

- Paper Last Run Phase Gate and current-vs-paper comparison sections.
- Backtest metrics and PnL sections.
- Quick navigation and related reports.
- Paper last run audit/readiness/execution sections.
- Public CLI command names or options.
- Summary key names, report text/order outside the extracted section, schemas, CI, dependencies, auth, DB, or paper/live safety boundary wording.

## Test Plan

1. RED: `CI=true timeout 120 uv run pytest -q tests/test_weekly_review_current_gate.py`
2. GREEN focused: same command passes.
3. Related weekly review tests:
   - `CI=true timeout 120 uv run pytest -q tests/test_weekly_review_current_gate.py tests/test_ops_reporting.py -k 'weekly_review'`
   - `CI=true timeout 120 uv run pytest -q tests/test_monitoring_comparison.py -k 'weekly_review'`
4. Static and broad checks:
   - `uv run ruff format src/sis/reports/weekly_review.py src/sis/reports/weekly_review_current_gate.py tests/test_weekly_review_current_gate.py`
   - `uv run ruff check src/sis/reports/weekly_review.py src/sis/reports/weekly_review_current_gate.py tests/test_weekly_review_current_gate.py`
   - `uv run ty check src --python-version 3.13 --output-format concise`
   - `uv run sis --help | wc -l`
   - `git diff --check`
   - `./scripts/check`

## Practical Review

- Risk: Markdown text/order changes. Mitigation: direct tests assert exact lines for populated and unavailable sections.
- Risk: diagnostics symbols formatting changes. Mitigation: direct test covers multiple symbols and filtering to string values.
- Risk: backtest symbol scope wording changes. Mitigation: direct test covers historical/legacy symbols and interpretation text.

## Rollback

Delete the new helper/test files and restore the current gate section logic directly in `src/sis/reports/weekly_review.py`.

## Branch Decision

Continue on existing dedicated refactor branch `refactor/backtest-primitives`. This is a small, behavior-preserving helper extraction and does not require a new branch under AGENTS.md.
