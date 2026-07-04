<!--
作成日: 2026-07-03_12:32 JST
更新日: 2026-07-03_12:42 JST
-->

# C9 Bridge Reversal Family Fail-Closed Plan

## Checkpoint ID

RC2-C9-REVERSAL-FAIL-CLOSED

## Purpose

`profit-core-reality-check` dogfood で次の1件として出た `UNSUPPORTED_FAMILY_DOMINATES` を、実際の blocker へ分解する。

対象 family は `perp_reversal_after_liquidation_move`。ただし現 source adapter は liquidation stream / `liquidation_notional` を materialize していないため、この family を `BRIDGED` に昇格しない。今回の完了状態は、unsupported family ではなく、`side_bias=both` は `BLOCKED_UNSUPPORTED_SIDE_BIAS`、`side_bias=short` は `BLOCKED_MISSING_SOURCE_COLUMNS` として fail-closed すること。

## Current Facts

- 現行 C9 bridge の bridgeable family は `perp_momentum_continuation` と `perp_funding_rate_carry_filter`。
- dogfood artifact は shortlisted 5件のうち 3件を `BRIDGED`、2件を `BLOCKED_UNSUPPORTED_FAMILY_MAPPING` にしている。
- blocked 2件はいずれも `perp_reversal_after_liquidation_move`。
- `cand-003-perp_reversal_after_liquidation_move` は `side_bias=both`。
- `cand-004-perp_reversal_after_liquidation_move` は `side_bias=short`。
- candidate の `feature_columns_used` は `liquidation_notional`, `mark_price`, `index_price`。
- 現 `prep_watchdeck_source.py` の `PrepWatchdeckBundle` は contracts、tickers、candles、quality、snapshot source を持つが、liquidation stream / liquidation notional を持たない。
- 既存 docs は、source rows / required columns が無い場合は `BLOCKED_MISSING_SOURCE_COLUMNS` にする、と定義している。

## Constraints

- `signal_expression` の自由文を parse / execute しない。
- `liquidation_notional` を価格変動、volume、open interest、funding から黙って推定しない。
- `side_bias=both` を short または long に勝手に変換しない。
- actual cash rows、actual-cash gate、demo/testnet、external API、live permission は触らない。
- public schema と CLI surface は変えない。
- `BRIDGED` は technical-only であり、profit proof ではない境界を維持する。

## Target Files

- `src/sis/strategy_idea_candidates/authoring_bridge.py`
- `tests/strategy_idea_candidates/test_authoring_bridge.py`
- `docs/strategy_idea_candidates/README.md`
- `docs/plans/2026-07-03-profit-core-reality-check/05_BLOCKER_TAXONOMY.md`
- `docs/plans/2026-07-03-profit-core-reality-check/06_NEXT_DECISION_AFTER_DOGFOOD.md`
- `docs/final-summary.md`
- `.ai-work/state.md`

## Implementation Approach

1. C9 bridge に family-aware blocked family として `perp_reversal_after_liquidation_move` を追加する。
2. 共通 blocker 判定は既存順序を維持する。
   - side bias
   - product type
   - symbol data
   - source columns
3. reversal family の `side_bias=both` は `BLOCKED_UNSUPPORTED_SIDE_BIAS` のまま止める。
4. reversal family の `side_bias=long|short` は、現 source では `liquidation_notional` が materialize できないため `BLOCKED_MISSING_SOURCE_COLUMNS` にする。
5. `perp_momentum_continuation` と `perp_funding_rate_carry_filter` の既存 `BRIDGED` 挙動は変えない。
6. docs は「bridgeable family は2つ、reversal は fail-closed recognition まで」と明記する。

## Test Plan

Focused:

```bash
uv run pytest tests/strategy_idea_candidates/test_authoring_bridge.py -q
```

Dogfood:

```bash
uv run sis strategy-idea-candidates-authoring-bridge \
  --candidate-set data/strategy_idea_candidates/c9-btcusdt-realdata-20260628T045945Z/candidates/strategy_idea_candidate_set.json \
  --export-manifest data/strategy_idea_candidates/c9-btcusdt-realdata-20260628T045945Z/candidates/exported_strategy_ideas/strategy_idea_candidate_export_manifest.json \
  --ledger data/strategy_idea_candidates/c9-btcusdt-realdata-20260628T045945Z/candidates/search_ledger.jsonl \
  --prep-watchdeck-root data/strategy_idea_candidates/c9-btcusdt-realdata-20260628T045945Z/bitget_public_source/source_root \
  --out data/profit_core_reality_check/dogfood/c9-reversal-fail-closed/authoring_bridge \
  --replace-existing
```

Then run `profit-core-reality-check` against that new bridge manifest and confirm `UNSUPPORTED_FAMILY_DOMINATES` no longer appears as the next single blocker.

Full:

```bash
./scripts/check
git diff --check
```

## Completion Conditions

- `perp_reversal_after_liquidation_move` no longer produces `BLOCKED_UNSUPPORTED_FAMILY_MAPPING`.
- `side_bias=both` reversal candidate stays blocked as `BLOCKED_UNSUPPORTED_SIDE_BIAS`.
- `side_bias=short` reversal candidate stays blocked as `BLOCKED_MISSING_SOURCE_COLUMNS` because liquidation source is absent.
- Existing bridgeable families still produce candidate-scoped artifacts and backtest packs.
- Dogfood reality check moves past `UNSUPPORTED_FAMILY_DOMINATES`.
- No generated `data/` artifact is committed.
- Full verification passes.

## Verification Record

- `uv run pytest tests/strategy_idea_candidates/test_authoring_bridge.py -q` -> 7 passed.
- Dogfood C9 bridge -> `status=pass`, `bridged_count=3`, `blocked_count=2`.
- Dogfood `profit-core-reality-check` -> `status=blocked`, `next_single_blocker_to_fix=UNSUPPORTED_SIDE_BIAS_DOMINATES`.
- `uv run python scripts/check_current_docs.py` -> checked 197 current docs.
- `git diff --check` -> passed.
- `./scripts/check` -> passed, including `2863 passed`.

## Failure Conditions

- The implementation converts `both` into a directional order.
- The implementation fabricates liquidation data from candles or estimates.
- `perp_reversal_after_liquidation_move` becomes `BRIDGED` without explicit liquidation source support.
- Existing momentum or funding candidates regress.
- docs imply profit proof, paper permission, live permission, or actual cash availability.

## Impact

This is a blocker-quality improvement, not an economic readiness improvement. It gives the next sprint a more truthful target: either add an explicit liquidation source adapter or define how to split/represent `both` without inventing orders.

## Rollback

Revert the changes in `authoring_bridge.py`, the focused tests, and the docs update. Runtime dogfood artifacts under `data/` are ignored and do not require git rollback.

## Alternatives

- Add real liquidation source support now: rejected for this checkpoint because the current dogfood source root does not contain that stream, and adding a new source adapter is a larger data-ingestion task.
- Approximate liquidation move from candle return: rejected because it would hide a required evidence gap.
- Treat `both` as short for this dataset: rejected because candidate semantics would be changed without an explicit rule.

## Critique Pass 1

Risk: The name `UNSUPPORTED_FAMILY_DOMINATES -> add one C9 family mapping` can tempt us to make the family bridge successfully. That is not justified by the current source. The candidate explicitly names `liquidation_notional`, and the source adapter does not expose it.

Correction: The mapping added here is a fail-closed recognition mapping only. It replaces an imprecise unsupported-family blocker with precise source/side blockers.

## Critique Pass 2

Risk: Moving the next blocker away from unsupported family can be misread as "closer to profit". It is not. It only says the code now knows what data is missing.

Correction: Verification must report the new blocker plainly. `BRIDGED` remains technical-only, and missing actual cash / risk review / source availability blockers remain in force.
