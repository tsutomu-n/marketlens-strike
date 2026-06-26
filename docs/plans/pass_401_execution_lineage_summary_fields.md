<!--
作成日: 2026-06-26_21:12 JST
更新日: 2026-06-26_21:12 JST
-->

# Pass 401 Execution Lineage Summary Fields

## Purpose

Extract execution snapshot and execution comparison summary normalization from `src/sis/reports/execution_lineage_normalizers.py` into a focused helper module.

## Scope

- Add `src/sis/reports/execution_lineage_summary_fields.py`.
- Move only:
  - bool-like string normalization used by execution comparison summaries.
  - execution snapshot summary alias normalization.
  - execution comparison summary alias normalization.
  - flat field builders for execution snapshot and comparison summaries.
- Keep the public import surface through `src/sis/reports/execution_lineage_normalizers.py` unchanged.
- Add direct tests for the new helper module while preserving existing `tests/test_execution_lineage_normalizers.py` behavior.

## Out Of Scope

- Latest execution lineage payload assembly.
- Latest execution lineage note parsing.
- Remapping or merging lineage fields.
- Markdown/flat line rendering in `execution_lineage_sections.py`.
- Public CLI command names or options.
- Summary key names, report text/order, schemas, CI, dependencies, auth, DB, or paper/live safety boundary wording.

## Test Plan

1. RED: `CI=true timeout 120 uv run pytest -q tests/test_execution_lineage_summary_fields.py`
2. GREEN focused: same command passes.
3. Related execution lineage tests:
   - `CI=true timeout 120 uv run pytest -q tests/test_execution_lineage_summary_fields.py tests/test_execution_lineage_normalizers.py tests/test_execution_lineage_sections.py`
   - `CI=true timeout 120 uv run pytest -q tests/test_execution_snapshot_report.py tests/test_execution_venue_comparison_report.py`
4. Static and broad checks:
   - `uv run ruff format src/sis/reports/execution_lineage_normalizers.py src/sis/reports/execution_lineage_summary_fields.py tests/test_execution_lineage_summary_fields.py`
   - `uv run ruff check src/sis/reports/execution_lineage_normalizers.py src/sis/reports/execution_lineage_summary_fields.py tests/test_execution_lineage_summary_fields.py`
   - `uv run ty check src --python-version 3.13 --output-format concise`
   - `uv run sis --help | wc -l`
   - `git diff --check`
   - `./scripts/check`

## Practical Review

- Risk: public imports break. Mitigation: keep aliases exported from `execution_lineage_normalizers.py` and run existing lineage tests.
- Risk: comparison bool normalization changes. Mitigation: direct tests cover string `"true"` and `"False"` aliases.
- Risk: snapshot/comparison flat field keys change. Mitigation: direct tests assert existing key names and alias behavior.

## Rollback

Delete the new helper/test files and restore the moved functions directly in `src/sis/reports/execution_lineage_normalizers.py`.

## Branch Decision

Continue on existing dedicated refactor branch `refactor/backtest-primitives`. This is a small, behavior-preserving helper extraction and does not require a new branch under AGENTS.md.
