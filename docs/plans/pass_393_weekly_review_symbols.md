<!--
作成日: 2026-06-26_19:50 JST
更新日: 2026-06-26_19:50 JST
-->

# Pass 393 Weekly Review Symbol Helpers

## Purpose

Extract side-effect-free weekly review symbol helpers from `src/sis/reports/weekly_review.py` into a focused helper
module.

## Scope

- Add `src/sis/reports/weekly_review_symbols.py`.
- Move canonical symbol extraction and backtest symbol scope classification.
- Keep existing private helper name `_canonical_symbols` available from `weekly_review.py` by explicit alias.
- Add direct tests for canonical symbol filtering/sorting and legacy/current scope classification.

## Out Of Scope

- Weekly review Markdown text or section ordering.
- Public CLI command names or options.
- Summary JSON key names or artifact key names.
- Paper/live safety boundary wording.
- Schemas, CI, dependencies, auth, DB, or external-service behavior.

## Test Plan

1. RED: `CI=true timeout 120 uv run pytest -q tests/test_weekly_review_symbols.py`
2. GREEN focused: same command passes.
3. Related report tests:
   - `CI=true timeout 120 uv run pytest -q tests/test_weekly_review_symbols.py tests/test_weekly_review_navigation.py`
   - `CI=true timeout 120 uv run pytest -q tests/test_ops_reporting.py -k 'weekly_review'`
   - `CI=true timeout 120 uv run pytest -q tests/test_monitoring_comparison.py -k 'weekly_review'`
   - `CI=true timeout 120 uv run pytest -q tests/test_cli_smoke.py -k 'weekly_review'`
4. Static and broad checks:
   - `uv run ruff format src/sis/reports/weekly_review.py src/sis/reports/weekly_review_symbols.py tests/test_weekly_review_symbols.py`
   - `uv run ruff check src/sis/reports/weekly_review.py src/sis/reports/weekly_review_symbols.py tests/test_weekly_review_symbols.py`
   - `uv run ty check src --python-version 3.13 --output-format concise`
   - `uv run sis --help | wc -l`
   - `git diff --check`
   - `./scripts/check`

## Practical Review

- Risk: symbol ordering changes. Mitigation: direct tests lock alphabetical canonical symbol output.
- Risk: invalid rows accidentally appearing in report output. Mitigation: direct tests cover missing, empty, and
  non-string canonical symbols.
- Risk: legacy scope wording drift. Mitigation: helper returns the existing exact scope strings used by
  `weekly_review.py`.

## Rollback

Delete the new helper/test files and restore the moved helper definitions in `src/sis/reports/weekly_review.py`.

## Branch Decision

Continue on existing dedicated refactor branch `refactor/backtest-primitives`. This is a small, behavior-preserving
helper extraction and does not require a new branch under AGENTS.md.
