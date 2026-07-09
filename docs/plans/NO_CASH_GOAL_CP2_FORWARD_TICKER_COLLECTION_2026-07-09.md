<!--
作成日: 2026-07-09_14:12 JST
更新日: 2026-07-09_15:14 JST
-->

# No-Cash Goal CP2 Forward Ticker Collection Plan

## Checkpoint

- ID: `CP2_FORWARD_TICKER_COLLECTION`
- Goal: reach a timestamp-safe real-market no-cash event/outcome set that can later be run through candidate pack and no-cash gate.
- Branch: `ai/no-cash-goal-forward-ticker-20260709-1555`

## Current State

- `crypto-perp-real-market-ticker-coverage-status` exists and is the source of truth for whether ticker-required sampling can proceed.
- Current observed status after one append run:
  - `decision=COLLECT_TICKER_SNAPSHOTS`
  - `ticker_covered_candidate_count=3`
  - `target_event_count=30`
  - `valid_bid_ask_row_count=3`
  - `HISTORICAL_TICKER_SOURCE_NOT_AVAILABLE=189`
  - `TICKER_SOURCE_STALE=227`
  - `HISTORICAL_TICKER_BID_ASK_NOT_AVAILABLE=0`
- This is not Paper Observation readiness and not backtest gate readiness.

## Constraints

- Do not start Paper Observation.
- Do not create paper orders, actual cash rows, wallet/signing use, exchange writes, live orders, or profit-proof claims.
- Do not reuse current ticker snapshots for old event cutoffs.
- Do not use market, mark, or index candles as bid/ask ticker coverage.
- Do not run `crypto-perp-real-market-no-cash-sample --require-ticker-coverage` until status is `READY_FOR_TICKER_REQUIRED_SAMPLE`.

## Target Files

- `docs/crypto_perp/NO_CASH_BACKTEST_GOAL_IMPLEMENTATION_PLAN_2026-07-08.md`
- `docs/crypto_perp/REAL_MARKET_TICKER_COVERAGE_STATUS_V1.md`
- `.ai-work/state.md`
- `.ai-work/checkpoints.md`
- `.ai-work/notes.md`

## Implementation Steps

1. Preserve the existing docs correction that changes CP2 from one-shot append to repeated forward collection.
2. Run one or more public append refresh cycles, then rerun ticker coverage status.
3. If status becomes `READY_FOR_TICKER_REQUIRED_SAMPLE`, run ticker-required sample, candidate pack, and no-cash gate.
4. If status remains `COLLECT_TICKER_SNAPSHOTS`, stop before gate and record the precise blocker class.
5. Keep issue #29 open until ticker-covered sample and no-cash gate evidence satisfy the goal.

## Test Plan

```bash
uv run sis crypto-perp-real-market-ticker-coverage-status \
  --source-root data/strategy_idea_candidates/btc-perp/bitget_public_source/source_root \
  --target-event-count 30 \
  --ticker-max-staleness-seconds 900 \
  --out data/crypto_perp/real_market_no_cash/ticker_coverage_status/latest
uv run pytest tests/crypto_perp/test_real_market_ticker_coverage_status.py -q
uv run pytest tests/crypto_perp/test_real_market_no_cash_sample.py tests/strategy_idea_candidates/test_bitget_public_source.py -q
uv run python scripts/check_current_docs.py
uv run python scripts/check_cli_catalog.py
git diff --check
./scripts/check
```

## Completion Conditions

- CP2 status reaches `READY_FOR_TICKER_REQUIRED_SAMPLE`, or the remaining ticker blocker is recorded precisely enough for the next loop.
- No false Paper Observation, paper order, live, actual cash, or profit-proof claims are introduced.
- Docs and checks pass.

## Failure Conditions

- Running ticker-required sample before status is ready.
- Treating a current snapshot as historical cutoff coverage.
- Claiming no-cash goal completion while gate is not `NO_CASH_BACKTEST_HOLD`.
- Closing issue #29 before ticker-covered gate evidence exists.

## Impact And Rollback

- Impact is limited to docs and ignored local runtime data under `data/`.
- Rollback is `git restore docs/crypto_perp/NO_CASH_BACKTEST_GOAL_IMPLEMENTATION_PLAN_2026-07-08.md docs/crypto_perp/REAL_MARKET_TICKER_COVERAGE_STATUS_V1.md docs/plans/NO_CASH_GOAL_CP2_FORWARD_TICKER_COLLECTION_2026-07-09.md`.
- Runtime data under `data/` is gitignored; no irreversible cleanup is required.

## Open Items

- Proxmox network inspection is not required for Bitget public ticker collection. It becomes relevant only if Windows-generated JVData/research packs must be transferred into Ubuntu.

## Diagnostics Addendum

CP2 now requires the ticker coverage status artifact to explain why covered candidates remain below target. The implementation must expose `diagnosis`, `coverage_shortfall`, candle/ticker timestamp ranges, matured ticker row count, future-unmatured ticker row count, and next maturity hint. Ready criteria remain unchanged: only `ticker_covered_candidate_count >= target_event_count` allows ticker-required sampling.
