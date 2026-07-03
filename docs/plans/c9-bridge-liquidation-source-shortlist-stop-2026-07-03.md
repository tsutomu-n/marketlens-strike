<!--
作成日: 2026-07-03_13:08 JST
更新日: 2026-07-03_13:14 JST
-->

# C9 Bridge Liquidation Source Shortlist Stop Plan

## Checkpoint ID

RC5-LIQUIDATION-SOURCE-SHORTLIST-STOP

## Purpose

`crypto-perp-risk-taker` profile の bridge-first shortlist に、現 C9 v0 public source では必要 source を満たせない liquidation family を載せない。

候補は削除しない。candidate inventory と search ledger には `REJECTED` として残し、source 不足理由を記録する。`liquidation_notional` を candle return、通常 fills、open interest、推定 proxy で埋めない。

## Current Facts

- Current dogfood は `next_single_blocker_to_fix=MISSING_SOURCE_COLUMNS_DOMINATES`。
- 対象 candidate は `perp_reversal_after_liquidation_move` の `side_bias=short`。
- C9 authoring bridge はこの family を family-aware blocker として扱い、`liquidation_notional` が無い場合は `BLOCKED_MISSING_SOURCE_COLUMNS` で止める。
- Repo-native Bitget public source refresh は contracts / tickers / 5m candles を作るが、`liquidation_notional` と `open_interest` は作らない。
- `perp_open_interest_liquidation_pressure` も feature columns に `open_interest` と `liquidation_notional` を要求する。

## Constraints

- Public schema / CLI surface は変えない。
- `liquidation_notional` を推定値で偽装しない。
- `perp_reversal_after_liquidation_move` と `perp_open_interest_liquidation_pressure` は inventory に残す。
- bridge 側の fail-closed blocker は残す。
- actual cash rows、actual-cash gate、demo/testnet、external LLM API、private Bitget API は触らない。

## Target Files

- `src/sis/strategy_idea_candidates/generator.py`
- `tests/strategy_idea_candidates/test_perp_profile.py`
- `docs/strategy_idea_candidates/README.md`
- `docs/action-required.md`
- `docs/final-summary.md`

## Implementation Approach

1. `_perp_shortlist_rejection_reason()` に `family` を渡す。
2. `crypto-perp-risk-taker` profile だけで、source 欠落が既知の liquidation family を shortlist 前に `REJECTED` にする。
3. `perp_reversal_after_liquidation_move` は `liquidation_notional` source 不足として記録する。
4. `perp_open_interest_liquidation_pressure` は `open_interest` と `liquidation_notional` source 不足として記録する。
5. non-directional side も同時に問題なら、rejection reason に両方を残す。

## Test Plan

```bash
uv run pytest tests/strategy_idea_candidates/test_perp_profile.py -q
uv run sis strategy-idea-candidates-build \
  --contract data/strategy_idea_candidates/c9-btcusdt-realdata-20260628T045945Z/input/strategy_input_contract.json \
  --validation data/strategy_idea_candidates/c9-btcusdt-realdata-20260628T045945Z/input/strategy_input_contract_validation.json \
  --profile crypto-perp-risk-taker \
  --candidate-cap 20 \
  --shortlist-count 5 \
  --candidate-set-id btcusdt-c9-realdata-candidates-no-liquidation \
  --out data/profit_core_reality_check/dogfood/c9-liquidation-source-stop/candidates \
  --replace-existing
uv run sis strategy-idea-candidates-authoring-bridge ...
uv run sis profit-core-reality-check ...
uv run python scripts/check_current_docs.py
git diff --check
./scripts/check
```

## Completion Conditions

- `perp_reversal_after_liquidation_move` is `REJECTED` before shortlist for C9 v0 bridge-first dogfood.
- `perp_open_interest_liquidation_pressure` records source absence if generated.
- Candidate inventory and search ledger still contain rejected candidates.
- No actual-cash, demo/testnet, external API, private Bitget API, or source fabrication is introduced.
- Dogfood no longer reports `MISSING_SOURCE_COLUMNS_DOMINATES` for `liquidation_notional`.

## Verification Record

- `uv run pytest tests/strategy_idea_candidates/test_perp_profile.py -q` -> 4 passed.
- Regenerated BTCUSDT C9 candidate set -> 11 total, 5 shortlisted, 6 rejected.
- Rejected before shortlist due source absence:
  - `cand-003-perp_reversal_after_liquidation_move`
  - `cand-004-perp_reversal_after_liquidation_move`
  - `cand-011-perp_open_interest_liquidation_pressure`
- Regenerated C9 bridge -> `bridged_count=4`, `blocked_count=1`.
- Regenerated `profit-core-reality-check` -> `next_single_blocker_to_fix=UNSUPPORTED_FAMILY_DOMINATES`.
- Current remaining bridge blocker: `perp_volatility_breakout_compression`.
- `uv run python scripts/check_current_docs.py` -> checked 200 current docs.
- `git diff --check` -> passed.
- `./scripts/check` -> passed, including `2867 passed`.

## Failure Conditions

- `liquidation_notional` is inferred from candles, regular fills, open interest, or another proxy.
- Reversal candidates disappear from inventory instead of being rejected with a reason.
- `side_bias=both` is silently mapped to one direction.
- Docs imply profit proof, paper permission, live permission, or actual cash availability.

## Critique Pass 1

Risk: Rejecting source-missing families in the generator may hide useful future research hypotheses.

Correction: This only changes shortlist eligibility for the `crypto-perp-risk-taker` bridge-first profile. The candidates remain in inventory and ledger as rejected rows with source-specific reasons.

## Critique Pass 2

Risk: This does not make the C9 dogfood fully bridged; it shifts the next blocker to unsupported volatility family mapping.

Correction: That is the truthful next blocker. It is better than keeping a candidate on the bridge path that requires a source the repo does not currently materialize.
