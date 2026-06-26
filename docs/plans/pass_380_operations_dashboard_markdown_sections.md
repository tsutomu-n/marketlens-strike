<!--
作成日: 2026-06-26_17:48 JST
更新日: 2026-06-26_17:48 JST
-->

# Pass 380: Operations Dashboard Markdown Section Extraction

## Purpose

Reduce `src/sis/reports/operations_dashboard_markdown.py` by moving the deterministic Overall and Decision State Markdown section builders into a dedicated helper module while preserving report text, section order, and CLI behavior.

## Current State

- Branch: `refactor/backtest-primitives`
- Baseline commit: `30e43d1`
- Existing worktree: Pass 377, Pass 378, and Pass 379 are verified but uncommitted.
- `src/sis/reports/operations_dashboard_markdown.py` is 374 lines and still mixes top-level rendering orchestration with section line construction.
- Existing `tests/test_operations_dashboard_markdown.py` covers broad rendered output, but not exact section helper line lists.

## Scope

Target files:

- `src/sis/reports/operations_dashboard_markdown.py`
- `src/sis/reports/operations_dashboard_markdown_sections.py`
- `tests/test_operations_dashboard_markdown_sections.py`
- `.codex/SP_STATE.md`
- `.codex/refactor_loop_2026-06-24.md`
- `.ai-work/state.md`
- `.ai-work/checkpoints.md`
- `.ai-work/notes.md`
- `./.ai_memory/HANDOFF.md`

## Out Of Scope

- Markdown text/order changes.
- Summary JSON key names or values.
- Operations dashboard summary construction.
- Public CLI command names or options.
- Schema, dependency, auth, DB, CI, external-service, paper/live, wallet, signing, or exchange-write changes.

## Implementation Plan

1. RED: add direct tests for exact Overall and Decision State section line lists.
2. GREEN: add `operations_dashboard_markdown_sections.py` with pure section helper functions.
3. GREEN: update `operations_dashboard_markdown.py` to delegate only those two deterministic sections.
4. REFACTOR: run focused section tests, existing operations dashboard Markdown test, CLI smoke slice, targeted lint/type/CLI checks, `git diff --check`, and `./scripts/check`.

## Acceptance Criteria

- New section helper tests pass.
- Existing operations dashboard Markdown test passes.
- Existing operations dashboard CLI smoke slice passes.
- `uv run sis --help` still renders.
- `git diff --check` passes.
- `./scripts/check` passes.
- `operations_dashboard_markdown.py` line count is reduced without changing report text/order or summary keys.

## Risk Review

- Risk: User-facing report text changes.
  Mitigation: direct tests assert exact line lists and existing rendered-output tests continue to run.
- Risk: The extraction crosses into large execution adapter section text.
  Mitigation: this pass stops at Overall and Decision State only.
- Risk: Summary keys accidentally change.
  Mitigation: helper functions only read the existing summary mapping.

## Rollback

Inline the two helper functions back into `operations_dashboard_markdown.py` and remove the new module/test. No runtime data migration is involved.

## Branch Decision

No new branch is created because the repository is already on the dedicated refactor branch `refactor/backtest-primitives`, and this pass is behavior-preserving, scoped, and reversible.
