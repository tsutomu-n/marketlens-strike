<!--
作成日: 2026-07-03_13:15 JST
更新日: 2026-07-03_13:21 JST
-->

# C9 Bridge Volatility Family Plan

## Checkpoint ID

RC6-VOLATILITY-FAMILY-BRIDGE

## Purpose

Current dogfood の `next_single_blocker_to_fix=UNSUPPORTED_FAMILY_DOMINATES` を、対象 family 1つだけで解消する。

対象は `perp_volatility_breakout_compression`。この family は current Bitget public source の 5m candles から `mark_return` と `realized_volatility` を作れるため、`liquidation_notional` のような外部 source 欠落ではない。

## Current Facts

- RC5 dogfood の bridge blocker は `perp_volatility_breakout_compression` 1件。
- Candidate parameter は `compression_lookback` と `expansion_z` を持つ。
- Existing bridge は candle close から `mark_return_<lookback>bars` と `realized_volatility_<lookback>bars` を作っている。
- Existing bridgeable family は `perp_momentum_continuation` と `perp_funding_rate_carry_filter`。
- Technical bridge は profit proof でも economic gate pass でもない。

## Constraints

- 追加するのは `perp_volatility_breakout_compression` だけ。
- `perp_basis_mark_index_spread`、`perp_liquidity_spread_filter`、liquidation / OI family は広げない。
- No schema / public CLI change.
- No external API, private Bitget API, demo/testnet, actual cash rows, or gate execution.
- `BRIDGED` remains technical-only.

## Target Files

- `src/sis/strategy_idea_candidates/authoring_bridge.py`
- `tests/strategy_idea_candidates/test_authoring_bridge.py`
- `docs/strategy_idea_candidates/README.md`
- `docs/strategy_idea_candidates/GOAL_AND_GLOSSARY.md`
- `docs/plans/strategy-idea-candidates-c9-prep-watchdeck-bridge-2026-06-28.md`
- `docs/final-summary.md`

## Implementation Approach

1. Add `perp_volatility_breakout_compression` to C9 v0 `SUPPORTED_FAMILIES`.
2. Add helper functions for C9 lookback and threshold:
   - momentum uses `lookback` and `breakout_z`.
   - volatility uses `compression_lookback` and `expansion_z`.
3. Feature panel writes `volatility_expansion_threshold_<lookback>bars` for the volatility family.
4. Entry rule uses directional `mark_return_<lookback>bars` against the family-specific threshold column.
5. Funding family behavior stays unchanged.

## Test Plan

```bash
uv run pytest tests/strategy_idea_candidates/test_authoring_bridge.py -q
uv run sis strategy-idea-candidates-authoring-bridge ...
uv run sis profit-core-reality-check ...
uv run python scripts/check_current_docs.py
git diff --check
./scripts/check
```

## Completion Conditions

- `perp_volatility_breakout_compression` candidate generates candidate-scoped spec / suite / bundle / backtest pack.
- Existing momentum and funding bridge tests still pass.
- BTCUSDT C9 dogfood no longer reports `UNSUPPORTED_FAMILY_DOMINATES` for volatility.
- Docs say bridgeability increased to exactly three families.
- Permission boundary remains false.

## Verification Record

- `uv run pytest tests/strategy_idea_candidates/test_authoring_bridge.py -q` -> 8 passed.
- Regenerated BTCUSDT C9 candidate set -> 11 total, 5 shortlisted, 6 rejected.
- Regenerated C9 bridge -> `bridged_count=5`, `blocked_count=0`.
- Regenerated `profit-core-reality-check` -> `next_single_blocker_to_fix=BRIDGED_TECHNICAL_ONLY`.
- Volatility feature panel contains `mark_return_48bars`, `realized_volatility_48bars`, and `volatility_expansion_threshold_48bars`.
- `uv run python scripts/check_current_docs.py` -> checked 201 current docs.
- `git diff --check` -> passed.
- `./scripts/check` -> passed, including `2868 passed`.

## Failure Conditions

- Volatility bridge is described as alpha, profit, paper, or live proof.
- Generic all-family mapping is introduced.
- Source-missing liquidation / OI families are allowed through.
- C9 v0 source assumptions are silently broadened.

## Critique Pass 1

Risk: The family name says compression, but the current parameter grid does not include a separate compression threshold.

Correction: The v0 bridge should only materialize a candle-derived expansion technical rule using existing `compression_lookback` and `expansion_z`. It must not claim a complete volatility-regime evaluator.

## Critique Pass 2

Risk: Making one more family `BRIDGED` can be misread as economic progress.

Correction: The reality-check summary must keep `bridge_success_semantics=technical_only`, `economic_gate_status=NOT_EVALUATED`, and `actual_cash_result_available=false`.
