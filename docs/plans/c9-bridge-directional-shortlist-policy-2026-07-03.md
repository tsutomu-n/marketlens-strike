<!--
作成日: 2026-07-03_12:56 JST
更新日: 2026-07-03_13:01 JST
-->

# C9 Bridge Directional Shortlist Policy Plan

## Checkpoint ID

RC4-DIRECTIONAL-SHORTLIST

## Purpose

`crypto-perp-risk-taker` profile の shortlist に、C9 v0 authoring bridge が変換できない `side_bias=both` / `side_bias=no_trade` を載せない。

候補は削除しない。candidate inventory と search ledger には `REJECTED` として残し、理由を記録する。これにより、方向を捏造せず、bridge-first dogfood の `UNSUPPORTED_SIDE_BIAS_DOMINATES` を generator 側で防ぐ。

## Current Facts

- C9 authoring bridge は Strategy Authoring spec の `rules.side` と order side を `long` または `short` として生成する。
- `side_bias=both` は現在 `BLOCKED_UNSUPPORTED_SIDE_BIAS` になる。
- `perp_reversal_after_liquidation_move` の default grid には `both` と `short` がある。
- `perp_basis_mark_index_spread` と `perp_open_interest_liquidation_pressure` にも `both` がある。
- `perp_liquidity_spread_filter` には `no_trade` がある。
- Current generator は risk modeling fields だけを見て shortlist し、`side_bias` の bridgeability を見ていない。
- Local Bitget public source refresh は contracts / tickers / history candles のみで、liquidation notional source は無い。

## Constraints

- `both` を `long` または `short` に変換しない。
- `no_trade` を売買 spec に変換しない。
- candidate inventory から非方向候補を削除しない。
- public schema / CLI surface は変えない。
- actual cash rows、actual-cash gate、demo/testnet、external LLM API、private Bitget API は触らない。

## Target Files

- `src/sis/strategy_idea_candidates/generator.py`
- `tests/strategy_idea_candidates/test_perp_profile.py`
- `docs/strategy_idea_candidates/README.md`
- `docs/action-required.md`
- `docs/final-summary.md`

## Implementation Approach

1. `crypto-perp-risk-taker` profile の `_perp_shortlist_rejection_reason()` に directional side check を足す。
2. `side_bias` が `long` / `short` 以外なら、`REJECTED` にして `shortlist_reason` を付けない。
3. rejection reason は C9 v0 の directional authoring bridge 境界を明示する。
4. `long` / `short` の既存候補は挙動を変えない。
5. C9 BTCUSDT dogfood を candidate generation から再実行し、shortlisted candidates から `both` が外れることを確認する。

## Test Plan

```bash
uv run pytest tests/strategy_idea_candidates/test_perp_profile.py -q
uv run sis strategy-idea-candidates-build \
  --contract data/strategy_idea_candidates/c9-btcusdt-realdata-20260628T045945Z/input/strategy_input_contract.json \
  --validation data/strategy_idea_candidates/c9-btcusdt-realdata-20260628T045945Z/input/strategy_input_contract_validation.json \
  --profile crypto-perp-risk-taker \
  --candidate-cap 20 \
  --shortlist-count 5 \
  --candidate-set-id btcusdt-c9-realdata-candidates-directional \
  --out data/profit_core_reality_check/dogfood/c9-directional-shortlist/candidates \
  --replace-existing
uv run sis strategy-idea-candidates-authoring-bridge ...
uv run sis profit-core-reality-check ...
uv run python scripts/check_current_docs.py
git diff --check
./scripts/check
```

## Completion Conditions

- Non-directional `side_bias` candidates are `REJECTED` before shortlist for `crypto-perp-risk-taker`.
- Rejected candidates remain in candidate inventory and ledger.
- C9 bridge dogfood no longer has `BLOCKED_UNSUPPORTED_SIDE_BIAS` from the regenerated candidate set.
- The next blocker moves to source availability, most likely `MISSING_SOURCE_COLUMNS_DOMINATES`.
- Full verification passes.

## Verification Record

- `uv run pytest tests/strategy_idea_candidates/test_perp_profile.py -q` -> 3 passed.
- Regenerated BTCUSDT C9 candidate set -> 11 total, 5 shortlisted, 6 rejected.
- Non-directional candidates rejected before shortlist: reversal `both`, basis `both`, liquidity `no_trade`, open-interest/liquidation `both`.
- Regenerated C9 bridge -> `bridged_count=4`, `blocked_count=1`.
- Regenerated `profit-core-reality-check` -> `next_single_blocker_to_fix=MISSING_SOURCE_COLUMNS_DOMINATES`.
- `uv run python scripts/check_current_docs.py` -> checked 199 current docs.
- `git diff --check` -> passed.
- `./scripts/check` -> passed, including `2866 passed`.

## Failure Conditions

- `both` is silently mapped to one direction.
- `no_trade` becomes an order spec.
- Candidate inventory drops rejected candidates.
- Existing `long` / `short` candidates stop shortlisting.
- Docs imply profit proof, paper permission, live permission, or actual cash availability.

## Critique Pass 1

Risk: Rejecting `both` at profile level may look like deleting hypothesis coverage.

Correction: This only affects shortlist eligibility for the `crypto-perp-risk-taker` bridge-first profile. The candidates remain in inventory with rejection reasons; no signal is silently dropped.

## Critique Pass 2

Risk: This does not solve liquidation source absence and can shift the blocker to `MISSING_SOURCE_COLUMNS_DOMINATES`.

Correction: That is the intended truthful next blocker. Moving from unsupported side semantics to explicit source absence is progress because it removes a semantic ambiguity without fabricating data.
