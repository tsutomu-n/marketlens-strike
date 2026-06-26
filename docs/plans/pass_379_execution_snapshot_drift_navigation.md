<!--
作成日: 2026-06-26_17:41 JST
更新日: 2026-06-26_17:41 JST
-->

# Pass 379: Execution Snapshot Drift Navigation Extraction

## Purpose

Reduce `src/sis/reports/execution_snapshot_drift_history.py` by moving report navigation map construction into a dedicated helper module while preserving report text, JSON summary keys, and CLI behavior.

## Current State

- Branch: `refactor/backtest-primitives`
- Baseline commit: `30e43d1`
- Existing worktree: Pass 377 and Pass 378 are verified but uncommitted.
- `src/sis/reports/execution_snapshot_drift_history.py` is 378 lines and mixes operation parsing, summary aggregation, navigation maps, Markdown rendering, and file writes.
- The low-risk boundary is `_quick_navigation()` and `_related_reports()` because they only derive deterministic path maps from `out_path`.

## Scope

Target files:

- `src/sis/reports/execution_snapshot_drift_history.py`
- `src/sis/reports/execution_snapshot_drift_history_navigation.py`
- `tests/test_execution_snapshot_drift_history_navigation.py`
- `.codex/SP_STATE.md`
- `.codex/refactor_loop_2026-06-24.md`
- `.ai-work/state.md`
- `.ai-work/checkpoints.md`
- `.ai-work/notes.md`
- `./.ai_memory/HANDOFF.md`

## Out Of Scope

- Operation-chain parsing or note filtering.
- Summary JSON key names or values.
- Markdown heading text, bullet text, or section order.
- Public CLI command names or options.
- Schema, dependency, auth, DB, CI, external-service, paper/live, wallet, signing, or exchange-write changes.

## Implementation Plan

1. RED: add direct tests for `quick_navigation()` and `related_reports()` including missing output handling and exact key order/path values.
2. GREEN: add `execution_snapshot_drift_history_navigation.py` with pure navigation helper functions.
3. GREEN: update `execution_snapshot_drift_history.py` to delegate only navigation map construction while preserving private helper aliases.
4. REFACTOR: run focused navigation tests, related CLI/report tests, targeted lint/type/CLI checks, `git diff --check`, and `./scripts/check`.

## Acceptance Criteria

- New navigation helper tests pass.
- Existing execution snapshot drift CLI/report slice passes.
- `uv run sis --help` still renders.
- `git diff --check` passes.
- `./scripts/check` passes.
- `execution_snapshot_drift_history.py` line count is reduced without changing report text/order or summary keys.

## Risk Review

- Risk: Navigation key order changes and affects rendered Markdown.
  Mitigation: direct tests assert exact dict order.
- Risk: The path map extraction accidentally changes summary payloads.
  Mitigation: helper functions accept only `out_path` and return path maps.
- Risk: Broader summary aggregation cleanup is tempting.
  Mitigation: this pass stops at navigation helpers and leaves aggregation/rendering untouched.

## Rollback

Inline the helper functions back into `execution_snapshot_drift_history.py` and remove the new module/test. No runtime data migration is involved.

## Branch Decision

No new branch is created because the repository is already on the dedicated refactor branch `refactor/backtest-primitives`, and this pass is behavior-preserving, scoped, and reversible.
