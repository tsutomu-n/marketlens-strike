<!--
作成日: 2026-06-26_20:13 JST
更新日: 2026-06-26_20:13 JST
-->

# Pass 395 Phase Gate Review Markdown Tables

## Purpose

Extract deterministic Markdown table line builders from `src/sis/reports/phase_gate_review_markdown.py` into a focused helper module.

## Scope

- Add `src/sis/reports/phase_gate_review_markdown_tables.py`.
- Move Diagnostics, Venue Decisions, and Execution Drift Classification Markdown line generation.
- Preserve table headers, separators, value fallback behavior, and pipe escaping exactly.
- Keep summary key names, report section order, public CLI behavior, and phase-gate decision logic unchanged.
- Add direct tests for table helpers, including empty/no-data fallbacks and pipe replacement.

## Out Of Scope

- Phase gate review decision logic.
- Remediation order, signal snapshot, recommendation, stop-condition, or artifact rendering.
- Summary JSON key names or artifact key names.
- Markdown section headings or report section ordering.
- Public CLI command names or options.
- Schemas, CI, dependencies, auth, DB, or paper/live safety boundary wording.

## Test Plan

1. RED: `CI=true timeout 120 uv run pytest -q tests/test_phase_gate_review_markdown_tables.py`
2. GREEN focused: same command passes.
3. Related report tests:
   - `CI=true timeout 120 uv run pytest -q tests/test_phase_gate_review_markdown_tables.py tests/test_phase_gate_review_markdown.py tests/test_phase_gate_review_markdown_values.py`
   - `CI=true timeout 120 uv run pytest -q tests/test_phase_gate_review.py -k 'phase_gate_review'`
   - `CI=true timeout 120 uv run pytest -q tests/test_cli_smoke.py -k 'phase_gate_review'`
4. Static and broad checks:
   - `uv run ruff format src/sis/reports/phase_gate_review_markdown.py src/sis/reports/phase_gate_review_markdown_tables.py tests/test_phase_gate_review_markdown_tables.py`
   - `uv run ruff check src/sis/reports/phase_gate_review_markdown.py src/sis/reports/phase_gate_review_markdown_tables.py tests/test_phase_gate_review_markdown_tables.py`
   - `uv run ty check src --python-version 3.13 --output-format concise`
   - `uv run sis --help | wc -l`
   - `git diff --check`
   - `./scripts/check`

## Practical Review

- Risk: Markdown table text or order drift. Mitigation: direct helper tests assert exact returned line lists, and existing full renderer tests remain in the verification slice.
- Risk: pipe escaping regression in classification columns. Mitigation: direct test includes pipe characters in reason/source/action values.
- Risk: no-data fallback drift for venue decisions or drift classifications. Mitigation: direct tests cover empty inputs.

## Rollback

Delete the new helper/test files and restore table line generation directly in `src/sis/reports/phase_gate_review_markdown.py`.

## Branch Decision

Continue on existing dedicated refactor branch `refactor/backtest-primitives`. This is a small, behavior-preserving helper extraction and does not require a new branch under AGENTS.md.
