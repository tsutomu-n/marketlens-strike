<!--
作成日: 2026-07-04_22:15 JST
更新日: 2026-07-04_22:15 JST
-->

# Pre Actual Cash Existing Artifact Read Plan

## Checkpoint ID

PAC-EXISTING-ARTIFACT-READ-2026-07-04

## Purpose

Make `build_pre_actual_cash_evidence_pack()` distinguish source gaps coming from existing readable artifacts from gaps produced by the writer's minimal recomputation path.

## Current State

The writer already selects event/outcome pairs, reads existing `crypto_perp_profit_readiness_run.v1` manifests, and can write the 11 expected pack artifacts. Before this checkpoint, it recomputed source availability, replay slice, feature pack, edge score, tournament rows v2, and bias guard from event/outcome inputs even when existing artifacts were present under `data_dir`.

## Constraints

- Do not add a public pre-actual-cash CLI.
- Do not add actual cash, cash ledger, actual-cash rows, tiny-live, live order, exchange write, wallet/signing, or ML/LLM decision behavior.
- Preserve existing summary artifact filenames.
- Keep schema compatibility; use existing permissive summary objects instead of requiring a schema migration.

## Target Files

- `src/sis/crypto_perp/pre_actual_cash.py`
- `tests/crypto_perp/test_profit_readiness_local_automation.py`
- `docs/crypto_perp/PRE_ACTUAL_CASH_DECISION_GATE.md`
- `docs/final-summary.md`

## Implementation Approach

Use the existing `build_profit_readiness_inventory()` classifications to locate known artifacts. Validate readable artifacts with their Pydantic models. Match per-event artifacts by `event_id`, match `tournament_rows_v2` by event set, and match `bias_guard` by event count while explicitly noting that the bias guard schema does not carry event ids.

When an artifact is used, write `artifact_origin=existing` and its path into the relevant summary. When an artifact is absent or unusable, preserve the existing minimal recomputation path and mark `artifact_origin=recomputed_minimal` with `artifact_gap_origin=minimal recomputed from event/outcome only`.

## Implementation Steps

1. Add internal loaders for existing source availability, replay slice, feature pack, edge score, tournament rows v2, and bias guard artifacts.
2. Update per-event artifact construction to prefer existing artifacts and fall back to recomputation.
3. Add origin metadata to the affected summaries and to `decision.source_gap_summary.artifact_usage`.
4. Add focused tests for both existing-artifact adoption and recomputed fallback.
5. Update current docs and final summary.

## Test Plan

- `uv run pytest tests/crypto_perp/test_profit_readiness_local_automation.py -q`
- `uv run ruff check src/sis/crypto_perp/pre_actual_cash.py tests/crypto_perp/test_profit_readiness_local_automation.py`
- `uv run ruff format --check src/sis/crypto_perp/pre_actual_cash.py tests/crypto_perp/test_profit_readiness_local_automation.py`
- `uv run python scripts/check_current_docs.py`
- `uv run sis --help | rg "pre-actual-cash|pre_actual_cash|evidence-pack" || true`

## Completion Conditions

- Existing readable artifacts are reflected in pack summaries.
- Missing artifacts are explicitly marked as minimal recomputation from event/outcome only.
- `decision.json` still validates against `crypto_perp_pre_actual_cash_decision.v1`.
- All `non_goal_flags` remain false.
- No pre-actual-cash public CLI is exposed.
- Focused pytest, Ruff, and current-docs checks pass.

## Failure Conditions

- Existing readable source artifacts are silently ignored.
- Existing artifact gaps cannot be distinguished from writer recomputation gaps.
- The implementation introduces actual cash, tiny-live, live order, wallet/signing, exchange write, or ML/LLM decision behavior.
- A public pre-actual-cash CLI appears.

## Impact Scope

Internal Crypto Perp pre-actual-cash builder/writer summaries only.

## Rollback

Revert this plan, `src/sis/crypto_perp/pre_actual_cash.py`, the focused test updates, `docs/crypto_perp/PRE_ACTUAL_CASH_DECISION_GATE.md`, and the corresponding `docs/final-summary.md` addendum.

## Alternative

Keep the old minimal recomputation-only behavior and document it. This was rejected because the goal explicitly asks the writer to read existing artifacts when it can.

## Open Issues

None requiring user action.

## Destructive Change

No.

## Branch

`ai/pre-actual-cash-existing-artifacts-20260704-2208`

## Migration

No migration is required.
