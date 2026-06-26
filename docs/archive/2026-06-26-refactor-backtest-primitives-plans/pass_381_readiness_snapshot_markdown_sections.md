<!--
作成日: 2026-06-26_17:56 JST
更新日: 2026-06-26_17:56 JST
-->

# Pass 381: Readiness Snapshot Markdown Section Extraction

## Purpose

Reduce `src/sis/reports/readiness_snapshot_markdown.py` by moving deterministic top Markdown section builders into a dedicated helper module while preserving report text, section order, and CLI behavior.

## Current State

- Branch: `refactor/backtest-primitives`
- Baseline commit: `30e43d1`
- Existing worktree: Pass 377, Pass 378, Pass 379, and Pass 380 are verified but uncommitted.
- `src/sis/reports/readiness_snapshot_markdown.py` is 365 lines and mixes rendering orchestration with section line construction.
- Existing `tests/test_readiness_snapshot_markdown.py` covers broad rendered output, but not exact top section line lists.

## Scope

Target files:

- `src/sis/reports/readiness_snapshot_markdown.py`
- `src/sis/reports/readiness_snapshot_markdown_sections.py`
- `tests/test_readiness_snapshot_markdown_sections.py`
- `.codex/SP_STATE.md`
- `.codex/refactor_loop_2026-06-24.md`
- `.ai-work/state.md`
- `.ai-work/checkpoints.md`
- `.ai-work/notes.md`
- `./.ai_memory/HANDOFF.md`

## Out Of Scope

- Markdown text/order changes.
- Summary JSON key names or values.
- Readiness summary construction.
- Execution adapter surface section changes.
- Public CLI command names or options.
- Schema, dependency, auth, DB, CI, external-service, paper/live, wallet, signing, or exchange-write changes.

## Implementation Plan

1. RED: add direct tests for exact Overall, Phase Gate, and Readiness Flags section line lists.
2. GREEN: add `readiness_snapshot_markdown_sections.py` with pure section helper functions.
3. GREEN: update `readiness_snapshot_markdown.py` to delegate only those three deterministic sections.
4. REFACTOR: run focused section tests, existing readiness snapshot Markdown test, CLI smoke slice, targeted lint/type/CLI checks, `git diff --check`, and `./scripts/check`.

## Acceptance Criteria

- New section helper tests pass.
- Existing readiness snapshot Markdown test passes.
- Existing readiness snapshot CLI/report slice passes.
- `uv run sis --help` still renders.
- `git diff --check` passes.
- `./scripts/check` passes.
- `readiness_snapshot_markdown.py` line count is reduced without changing report text/order or summary keys.

## Risk Review

- Risk: User-facing report text changes.
  Mitigation: direct tests assert exact line lists and existing rendered-output tests continue to run.
- Risk: The extraction expands into the large execution adapter section.
  Mitigation: this pass stops before Strict Validation Preview and Execution Adapter Surfaces.
- Risk: Summary keys accidentally change.
  Mitigation: helper functions only read the existing summary mapping.

## Rollback

Inline the three helper functions back into `readiness_snapshot_markdown.py` and remove the new module/test. No runtime data migration is involved.

## Branch Decision

No new branch is created because the repository is already on the dedicated refactor branch `refactor/backtest-primitives`, and this pass is behavior-preserving, scoped, and reversible.
