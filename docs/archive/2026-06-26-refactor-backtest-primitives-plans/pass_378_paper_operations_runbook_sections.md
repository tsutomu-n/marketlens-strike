<!--
作成日: 2026-06-26_17:33 JST
更新日: 2026-06-26_17:33 JST
-->

# Pass 378: Paper Operations Runbook Status Section Extraction

## Purpose

Reduce `src/sis/reports/paper_operations_runbook.py` by moving the top, deterministic Markdown section line builders into a small helper module while preserving the exact report text and order.

## Current State

- Branch: `refactor/backtest-primitives`
- Baseline commit: `30e43d1`
- Existing worktree: Pass 377 is verified but uncommitted.
- `src/sis/reports/paper_operations_runbook.py` is 451 lines and still mixes summary loading, remediation context wiring, Markdown section rendering, and file writes.
- Path, navigation, base summary, and remediation context helpers are already extracted into dedicated modules.

## Scope

Target files:

- `src/sis/reports/paper_operations_runbook.py`
- `src/sis/reports/paper_operations_runbook_sections.py`
- `tests/test_paper_operations_runbook_sections.py`
- `.codex/SP_STATE.md`
- `.codex/refactor_loop_2026-06-24.md`
- `.ai-work/state.md`
- `.ai-work/checkpoints.md`
- `.ai-work/notes.md`
- `./.ai_memory/HANDOFF.md`

## Out Of Scope

- Public CLI command names or options.
- Summary JSON key names or artifact paths.
- Markdown heading text, bullet text, or section order.
- Remediation ordering, signal diff logic, or recommendation logic.
- Paper/live safety boundaries.
- Dependency, schema, auth, DB, CI, or external-service changes.

## Implementation Plan

1. RED: add direct tests for the new helper module covering:
   - current schedule section lines.
   - current daemon context section lines.
   - current status section lines and exact order for representative fields.
   - current remediation queue section lines and exact order.
2. GREEN: add `paper_operations_runbook_sections.py` with pure functions returning lists of Markdown lines.
3. GREEN: update `paper_operations_runbook.py` to use the helper functions for only those top sections.
4. REFACTOR: run focused tests, related CLI smoke slice, lint/type/CLI checks, `git diff --check`, and `./scripts/check`.

## Acceptance Criteria

- New section helper tests pass.
- Existing `paper-operations-runbook` CLI smoke slice passes.
- `uv run sis --help` still renders.
- `git diff --check` passes.
- `./scripts/check` passes.
- `paper_operations_runbook.py` line count is reduced without changing report text/order.

## Risk Review

- Risk: Report text or order changes because these strings are user-facing.
  Mitigation: direct tests assert exact line lists before extraction.
- Risk: The section extraction accidentally changes summary construction.
  Mitigation: helper functions only read the already-built `summary` and `daemon_manifest`.
- Risk: Broad runbook remediation rendering is tempting to clean.
  Mitigation: this pass stops at top deterministic sections and leaves remediation sections unchanged.

## Rollback

Revert the new helper import and inline the helper call results back into the existing `lines` list. No schema, dependency, or runtime data migration is involved.

## Branch Decision

No new branch is created because the repository is already on the dedicated refactor branch `refactor/backtest-primitives`, and this pass is behavior-preserving, scoped, and reversible.
