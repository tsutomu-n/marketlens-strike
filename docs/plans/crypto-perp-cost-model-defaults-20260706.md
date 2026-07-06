<!--
作成日: 2026-07-06_12:22 JST
更新日: 2026-07-06_12:22 JST
-->

# Crypto Perp Cost Model Defaults Plan 2026-07-06

## Checkpoint ID

CP-issue-22-cost-model-defaults

## Purpose

Unify Crypto Perp normal cost assumptions across tournament rows, pre-actual-cash, and backtest candidate pack while keeping stress/conservative assumptions explicit and paper-only.

## Current State

- Project taker fee assumption is `0.0004`.
- `backtest_candidate_pack` already defaults to fee `0.0004` and slippage `2`.
- `tournament_rows.py`, `pre_actual_cash.py`, and `crypto-perp-tournament-rows-v2` still default to fee `0.0006` and slippage `0`.
- `configs/cost_models/crypto_perp_bitget_usdt_futures.yaml` still describes `0.0006` as an implementation default for the candidate pack, which is stale after PR #21.

## Constraints

- Do not claim profit, actual cash readiness, tiny-live readiness, live readiness, wallet readiness, signing readiness, exchange-write readiness, or production order readiness.
- Keep `NO_TRADE` valid.
- Do not zero-fill missing books, trades, replay, cash ledger, or measurement artifacts.
- Keep changes scoped to Crypto Perp cost assumptions, tests, and current docs.

## Target Files

- `src/sis/crypto_perp/cost_model.py`
- `src/sis/crypto_perp/tournament_rows.py`
- `src/sis/crypto_perp/pre_actual_cash.py`
- `src/sis/crypto_perp/backtest_candidate_pack.py`
- `src/sis/commands/crypto_perp_backtest_candidate_pack.py`
- `src/sis/commands/crypto_perp_profit_readiness.py`
- `configs/cost_models/crypto_perp_bitget_usdt_futures.yaml`
- `tests/crypto_perp/test_tournament_rows.py`
- `tests/crypto_perp/test_backtest_candidate_pack.py`
- `tests/crypto_perp/test_profit_readiness_local_automation.py`
- `tests/crypto_perp/test_bias_guards.py`
- `docs/crypto_perp/BACKTEST_CANDIDATE_PACK_V1.md`
- `docs/runbooks/CRYPTO_PERP_TRUTH_CYCLE_RUNBOOK.md`
- `docs/crypto_perp/FOLLOWUP_REMEDIATION_2026-07-05.md`
- `docs/CURRENT_DOCS_INDEX_2026-07-05.md`

## Implementation Approach

Create one small code source for normal project assumptions and stress multiplier constants. Wire API and CLI defaults to that source. Keep config as the documented reference and align it with those constants. Add tests that fail on hidden `0.0006`, zero slippage, or zero-cost acceptance.

## Steps

1. Add shared Crypto Perp cost model constants for project fee, project funding estimate, project slippage, and stress slippage multiplier.
2. Replace duplicated API and CLI defaults with shared constants.
3. Reject zero fee and zero slippage in cost-aware tournament rows, matching backtest candidate pack validation.
4. Update tests for normal fee, stress slippage, CLI defaults, pre-actual-cash propagation, and zero-cost rejection.
5. Update config and docs to distinguish project assumption from stress/conservative scenario.
6. Run focused tests, docs/catalog checks, diff check, and `./scripts/check`.

## Test Plan

- `uv run pytest tests/crypto_perp/test_tournament_rows.py tests/crypto_perp/test_backtest_candidate_pack.py tests/crypto_perp/test_profit_readiness_local_automation.py tests/crypto_perp/test_bias_guards.py -q`
- `uv run pytest tests/crypto_perp -q`
- `uv run python scripts/check_current_docs.py`
- `uv run python scripts/check_cli_catalog.py`
- `git diff --check`
- `./scripts/check`

## Completion Criteria

- Normal project defaults are fee `0.0004`, funding `0.0001`, and slippage `2` across the targeted surfaces.
- Stress rows remain paper-only and are driven by explicit stress multiplier behavior.
- Zero-cost tournament row/backtest candidate pack inputs are rejected.
- Docs and config no longer describe stale `0.0006` as the backtest candidate pack default.

## Failure Conditions

- Existing actual-cash boundaries are weakened.
- Missing market data is silently treated as available.
- Stress/conservative assumptions are represented as measured actual cash.
- CLI catalog or current-doc checks fail.

## Impact Scope

Crypto Perp local simulation and pre-actual-cash estimate surfaces only. No exchange write path, wallet/signing path, or live order path is added.

## Rollback

Revert the shared constants module plus the default/validation/test/doc changes. Existing explicit caller-provided fee/slippage values remain accepted if positive.

## Alternatives

- Runtime-load YAML config from every builder. Rejected for this checkpoint because it expands IO/error surface and is unnecessary to remove hidden defaults.
- Keep `0.0006` as conservative default. Rejected because issue #22 explicitly makes `0.0004` the project assumption and requires stress/conservative assumptions to be explicit.

## Unresolved Items

None requiring user judgment.

## Breaking Change

Zero-cost cost-aware tournament rows become invalid. This is intentional because issue #22 requires zero-cost simulation to be forbidden.

## Branch

`ai/unify-crypto-perp-cost-model-defaults-20260706`
