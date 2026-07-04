<!--
作成日: 2026-06-28_09:34 JST
更新日: 2026-06-28_09:34 JST
-->

# Strategy Candidate Metrics And Perp Bridge Implementation Plan

## Checkpoint ID

CP1-CP6: selection-adjusted metrics, Perp cost estimates, Perp estimate bridge, split materialization, richer review packet, and Strategy Authoring preflight.

## Purpose

Complete the remaining local/offline strategy idea candidate work without creating live, wallet, signing, exchange-write, paper approval, or actual-cash profit claims.

## Current State

- `strategy-idea-candidates-build` writes a candidate set, Markdown report, search ledger, operator review Markdown, and optional `strategy_idea.v1` shortlist export.
- Perp candidates carry risk metadata in `parameter_set`.
- `selection_adjusted_metrics_status` currently allows and emits `NOT_IMPLEMENTED`.
- `crypto_perp_tournament_rows.v2` already represents cost-adjusted estimates and keeps `actual_cash_result_usd` nullable.
- `crypto-perp-tournament-report` remains actual-cash guarded.

## Constraints

- Do not call external APIs.
- Do not use wallet, signing, exchange write, live orders, paper permission, or actual-cash evidence.
- Do not make `strategy_idea.v1` carry candidate inventory provenance.
- Do not call raw metrics alpha proof or profit proof.
- Keep existing candidate set shape backward-compatible except additive enum/status support.

## Target Files

- `src/sis/strategy_idea_candidates/models.py`
- `src/sis/strategy_idea_candidates/generator.py`
- `src/sis/strategy_idea_candidates/selection_metrics.py`
- `src/sis/strategy_idea_candidates/perp_costs.py`
- `src/sis/strategy_idea_candidates/perp_bridge.py`
- `src/sis/strategy_idea_candidates/splits.py`
- `src/sis/strategy_idea_candidates/review_packet.py`
- `src/sis/strategy_idea_candidates/authoring_preflight.py`
- `src/sis/commands/strategy_idea_candidates.py`
- `schemas/strategy_idea_candidate_set.v1.schema.json`
- `tests/strategy_idea_candidates/*`
- `tests/crypto_perp/*` where actual-cash guard coverage is closest.

## Implementation Policy

1. Add a small selection-adjusted metrics engine:
   - `AVAILABLE` only when raw p-values exist and Benjamini-Hochberg FDR can be computed.
   - `NOT_ESTIMABLE` when the engine ran but required raw data is absent.
   - DSR, PBO, and White Reality Check stay explicit `NOT_ESTIMABLE` unless their required inputs exist.
2. Add Perp cost estimates:
   - Deterministic local estimates from candidate parameters.
   - Fee, funding, slippage, stress slippage, leverage, liquidation buffer, and max loss fields recorded.
   - Evidence level stays `local_parameter_estimate`.
3. Add candidate Perp estimate bridge:
   - Build candidate-scoped `crypto_perp_tournament_rows.v2` row sets from local outcome artifacts.
   - Keep `actual_cash_result_usd=null` and evidence level `cost_adjusted_estimate`.
4. Add split materialization:
   - Write split windows and policy record sidecar.
   - Preserve `uses_sealed_test_for_selection=false`.
5. Add richer review packet:
   - JSON and Markdown packet for human review.
   - Include human decision template and known gaps.
6. Add Strategy Authoring preflight:
   - Show `strategy_idea.v1` export availability.
   - Keep authoring/backtest/paper/live readiness false unless future artifacts prove otherwise.

## Implementation Steps

1. Add failing tests for metric status, cost estimates, sidecar build outputs, bridge rows, split sidecar, review packet, and preflight.
2. Implement new small modules under `src/sis/strategy_idea_candidates/`.
3. Wire `strategy-idea-candidates-build` to enrich candidate sets and write sidecars.
4. Add `strategy-idea-candidates-perp-estimate` CLI for outcome-backed estimate bridge.
5. Update docs only where current state wording would otherwise be false.
6. Run focused tests and repo checks.

## Test Policy

- Focused tests under `tests/strategy_idea_candidates`.
- Bridge and actual-cash guard tests under `tests/crypto_perp` only when closest to existing behavior.
- Validate `strategy_idea.v1` export and `strategy-intake-validate` remains passing.
- Run `git diff --check`.

## Completion Conditions

- Candidate build outputs sidecars for selection metrics, Perp cost estimates, split materialization, review packet, and authoring preflight.
- Perp estimate bridge produces cost-adjusted estimate artifacts only.
- Actual-cash tournament report still rejects non-actual-cash rows.
- `NOT_IMPLEMENTED` is no longer emitted for implemented local selection metrics in freshly built candidate sets.
- No live/paper/wallet/signing/exchange-write permission is introduced.

## Failure Conditions

- Any artifact claims actual-cash profit proof from estimates.
- Any CLI attempts network, wallet, signing, exchange write, or live order.
- `strategy-intake-validate` fails for existing shortlist export.
- Existing focused tests regress.

## Impact Scope

Strategy idea candidate generation and local crypto-perp estimate artifacts only. No venue write path, order path, account path, DB schema, or CI deployment behavior changes.

## Rollback Policy

Revert the new modules, command registrations, schema enum addition, and tests. Existing candidate build/export behavior can remain functional because changes are additive.

## Alternatives

- Leave selection metrics as `NOT_IMPLEMENTED`: rejected because user explicitly requested implementation.
- Implement full DSR/PBO/Reality Check: rejected for this slice because required raw return distributions and fold outcomes are not present in candidate artifacts.
- Feed estimates into `crypto-perp-tournament-report`: rejected because that report is actual-cash only.

## Unresolved Items

None requiring user action for this local/offline implementation. Real exchange cost evaluation and actual-cash proof remain future work requiring data and approval boundaries outside this task.

## Destructive Change

No.

## Branch

`ai/strategy-candidate-metrics-bridge-20260628-0931`

## Migration

No migration required. Existing candidate artifacts remain readable. New builds may use `NOT_ESTIMABLE`, which is added to the candidate set schema enum.
