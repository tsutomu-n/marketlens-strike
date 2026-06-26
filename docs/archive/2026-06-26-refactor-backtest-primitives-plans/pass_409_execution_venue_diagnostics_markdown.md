<!--
作成日: 2026-06-26_22:15 JST
更新日: 2026-06-26_22:15 JST
-->

# Pass 409 Execution Venue Diagnostics Markdown Helper

## Purpose

Extract Execution Venue Diagnostics Markdown line rendering from `src/sis/reports/execution_venue_diagnostics.py` into a dedicated helper module.

## Scope

Target files:

- `src/sis/reports/execution_venue_diagnostics.py`
- `src/sis/reports/execution_venue_diagnostics_markdown.py`
- `tests/test_execution_venue_diagnostics_markdown.py`

State files:

- `.codex/SP_STATE.md`
- `.codex/refactor_loop_2026-06-24.md`
- `.ai-work/state.md`
- `.ai-work/checkpoints.md`
- `.ai-work/notes.md`
- `.ai_memory/HANDOFF.md`

## Out Of Scope

- Execution venue diagnostics summary computation.
- Execution venue comparison summary loading.
- Navigation path map construction.
- Recommended read order construction.
- Summary JSON keys or values.
- Public CLI names, options, help text, exit codes, or stdout behavior.
- Schemas, dependencies, auth, DB, CI, external-service behavior, paper/live safety boundaries.

## Current Evidence

- `src/sis/reports/execution_venue_diagnostics.py` is 221 lines and combines summary loading, diagnostics summary assembly, navigation maps, Markdown rendering, file writing, and JSON writing.
- Existing report behavior is covered by `tests/test_execution_venue_diagnostics_report.py`.
- Existing CLI behavior is covered by `tests/test_cli_smoke.py::test_execution_venue_diagnostics_cli`.
- Current branch is `refactor/backtest-primitives`.
- Pass 405 through Pass 408 are verified but uncommitted on top of `27af86d`; preserve them.

## Plan

1. RED: add direct tests for a new `execution_venue_diagnostics_report_lines(...)` helper covering navigation and overview output.
2. GREEN: add `src/sis/reports/execution_venue_diagnostics_markdown.py` and move only Markdown line assembly into it.
3. Refactor `build_execution_venue_diagnostics_report(...)` to delegate line rendering to the helper while preserving summary assembly, file writing, and JSON writing.
4. Run focused and related tests, targeted lint/type checks, CLI help smoke, `git diff --check`, and full `./scripts/check`.

## Acceptance

- Direct helper tests pass.
- Existing execution venue diagnostics report tests still pass.
- CLI smoke for `execution-venue-diagnostics` still passes.
- `uv run sis --help` still renders.
- `git diff --check` passes.
- Full `./scripts/check` passes before broad completion is claimed.

## Practical Review

- Risk: Markdown text or order changes.
  - Mitigation: direct tests lock representative output lines, and existing report/CLI tests remain in the verification path.
- Risk: summary key changes.
  - Mitigation: summary assembly stays in `execution_venue_diagnostics.py`; helper receives already-built summary data.
- Risk: changing diagnostics calculation.
  - Mitigation: loading and gap/span calculation are outside the extraction.
