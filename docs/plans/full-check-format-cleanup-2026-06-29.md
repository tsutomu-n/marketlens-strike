<!--
作成日: 2026-06-29_18:57 JST
更新日: 2026-06-29_18:57 JST
-->

# Full Check Format Cleanup Plan

## Checkpoint ID

CP2 full-check-format-cleanup

## Purpose

Make full `./scripts/check` green by fixing the Ruff format gate failure that currently affects exactly 8 files.

## Current State

- Current branch: `ai/risk-taker-review-artifact-20260628-1721`.
- Start status: only untracked `codex_diag.sh`.
- `uv run ruff check <8 files>` passes.
- `uv run ruff format --check <8 files>` fails because all 8 target files would be reformatted.

## Constraints

- Do not touch `codex_diag.sh`.
- Do not change API, schemas, dependencies, external connections, DB, CI, or runtime behavior.
- Do not fix unrelated full-check failures inside CP2. If full check fails after formatting for another reason, record that failure and stop.
- Continue on the existing dedicated AI branch; do not create a new branch.

## Target Files

- `src/sis/strategy_idea_candidates/authoring_preflight.py`
- `src/sis/strategy_idea_candidates/perp_bridge.py`
- `src/sis/strategy_idea_candidates/perp_costs.py`
- `src/sis/strategy_idea_candidates/prep_watchdeck_source.py`
- `src/sis/strategy_idea_candidates/selection_metrics.py`
- `src/sis/strategy_idea_candidates/splits.py`
- `tests/strategy_idea_candidates/test_candidate_cli.py`
- `tests/strategy_idea_candidates/test_metrics_costs_bridge.py`

## Implementation Approach

Run `uv run ruff format` on only the 8 target files. No manual behavior edits are planned.

## Implementation Steps

1. Record CP2 in `.ai-work/state.md` and `.ai-work/checkpoints.md`.
2. Create this plan under `docs/plans/`.
3. Run `uv run ruff format <8 files>`.
4. Re-run targeted Ruff format and lint checks.
5. Run full `./scripts/check`.
6. Run whitespace and final diff/status checks.
7. Update `.ai-work/state.md`, `.ai-work/checkpoints.md`, and `docs/final-summary.md` with CP2 results.

## Test Plan

- `uv run ruff format --check <8 files>`
- `uv run ruff check <8 files>`
- `./scripts/check`
- `git diff --check`
- `git diff --stat`
- `git status --short --branch --untracked-files=all`

## Completion Conditions

- Full `./scripts/check` exits 0.
- `git diff --check` exits 0.
- Tracked code changes are limited to Ruff formatting in the 8 target files.
- CP2 documentation records the result and notes that `codex_diag.sh` remains untouched.

## Failure Conditions

- Full `./scripts/check` fails for a non-format reason.
- Formatting touches files outside the 8 target files.
- Any tracked diff changes behavior instead of formatting.

## Impact Scope

Low. This checkpoint affects only formatting and local work documentation.

## Rollback Plan

Revert the format-only diffs in the 8 target files and remove the CP2 plan/work-summary additions.

## Alternatives

- Run `uv run ruff format .`: rejected because the checkpoint is scoped to only the 8 known failing files.
- Manually rewrap code: rejected because Ruff is the authoritative formatter for this gate.

## Unresolved Items

None.

## Destructive Change

No.

## Branch

`ai/risk-taker-review-artifact-20260628-1721`

## Migration

No migration is required.

## Critique

The plan directly targets the observed format gate failure and avoids broad cleanup. The main risk is discovering a later non-format failure in `./scripts/check`; if that happens, CP2 should stop and record the next smallest checkpoint instead of expanding scope.
