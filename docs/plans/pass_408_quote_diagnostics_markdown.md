<!--
作成日: 2026-06-26_22:09 JST
更新日: 2026-06-26_22:09 JST
-->

# Pass 408 Quote Diagnostics Markdown Helper

## Purpose

Extract Quote Diagnostics Markdown line rendering from `src/sis/reports/quote_diagnostics.py` into a dedicated helper module.

## Scope

Target files:

- `src/sis/reports/quote_diagnostics.py`
- `src/sis/reports/quote_diagnostics_markdown.py`
- `tests/test_quote_diagnostics_markdown.py`

State files:

- `.codex/SP_STATE.md`
- `.codex/refactor_loop_2026-06-24.md`
- `.ai-work/state.md`
- `.ai-work/checkpoints.md`
- `.ai-work/notes.md`
- `.ai_memory/HANDOFF.md`

## Out Of Scope

- Quote diagnostic calculation logic.
- Quote file discovery or JSONL loading.
- Summary JSON keys or values.
- Quick navigation or related report path construction.
- Public CLI names, options, help text, exit codes, or stdout behavior.
- Schemas, dependencies, auth, DB, CI, external-service behavior, paper/live safety boundaries.

## Current Evidence

- `src/sis/reports/quote_diagnostics.py` is 321 lines and combines quote diagnostics calculation, navigation maps, summary assembly, Markdown rendering, file writing, and JSON writing.
- Existing report behavior is covered by `tests/test_monitoring_comparison.py::test_build_quote_diagnostics_report`.
- Existing calculation behavior is covered by `tests/test_quote_diagnostics.py`.
- Current branch is `refactor/backtest-primitives`.
- Pass 405 through Pass 407 are verified but uncommitted on top of `27af86d`; preserve them.

## Plan

1. RED: add direct tests for a new `quote_diagnostics_report_lines(...)` helper covering populated and empty diagnostics output.
2. GREEN: add `src/sis/reports/quote_diagnostics_markdown.py` and move only Markdown line assembly into it.
3. Refactor `build_quote_diagnostics_report(...)` to delegate line rendering to the helper while preserving summary assembly, file writing, and JSON writing.
4. Run focused and related tests, targeted lint/type checks, CLI help smoke, `git diff --check`, and full `./scripts/check`.

## Acceptance

- Direct helper tests pass.
- Existing quote diagnostics report test still passes.
- CLI smoke for `diagnose-quotes` still passes.
- `uv run sis --help` still renders.
- `git diff --check` passes.
- Full `./scripts/check` passes before broad completion is claimed.

## Practical Review

- Risk: Markdown text or order changes.
  - Mitigation: direct tests lock representative populated and empty output lines, and existing report tests remain in the verification path.
- Risk: summary key changes.
  - Mitigation: summary assembly stays in `quote_diagnostics.py`; helper receives already-built summary data.
- Risk: calculation behavior drift.
  - Mitigation: `build_quote_diagnostics(...)` and existing calculation tests are not changed.
