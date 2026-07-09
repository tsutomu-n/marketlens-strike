<!--
作成日: 2026-07-07_19:12 JST
更新日: 2026-07-09_10:48 JST
-->

# Issue 29 Ticker/Funding Source Coverage Plan

## Checkpoint

CP7: add a local status artifact that monitors whether forward-collected public ticker snapshots are sufficient for ticker-required no-cash sample selection.

## Purpose

Remove ticker blockers only when native ticker rows are timestamp-safe and include bid/ask. Historical price, mark, or index candles alone do not clear ticker coverage. Since Bitget public REST provides current snapshots rather than historical bid/ask rows, repeated `--append-existing` refreshes collect forward ticker history for future event cutoffs. Funding remains independent through historical funding rows.

## Constraints

No credentialed API, wallet/signing, exchange write, paper/live order, actual cash rows, profit proof, zero-filled ticker/funding, fabricated funding, dropped losing events, or manual `NO_TRADE` override.

## Target Files

- `src/sis/crypto_perp/ticker_source.py`
- `src/sis/crypto_perp/funding_source.py`
- `src/sis/crypto_perp/real_market_no_cash_sample.py`
- `src/sis/strategy_idea_candidates/bitget_public_source.py`
- `src/sis/commands/crypto_perp_real_market_no_cash_sample.py`
- `tests/crypto_perp/test_real_market_no_cash_sample.py`
- `tests/strategy_idea_candidates/test_bitget_public_source.py`
- `docs/crypto_perp/REAL_MARKET_NO_CASH_SAMPLE_V1.md`

## Implementation

Use `build_ticker_source_status` to keep the existing timestamp-safe ticker rules. `crypto-perp-real-market-ticker-coverage-status` reads local candles and ticker rows, counts ticker-covered candidate windows, and emits either `COLLECT_TICKER_SNAPSHOTS` with an exact `--append-existing` command or `READY_FOR_TICKER_REQUIRED_SAMPLE` with an exact `--require-ticker-coverage` command. Keep funding independent as reference-only status. Leave books/trades/replay as known gaps.

## Tests

Add deterministic ticker coverage status fixtures. Verify no ticker rows, future-only rows, stale rows, missing bid/ask rows, insufficient covered windows, ready covered windows, CLI stdout, JSON/Markdown output, boundary flags, docs checks, CLI catalog check, `git diff --check`, and `./scripts/check`.

## Failure Conditions

If public source rows are after event cutoffs, stale, or too sparse for the requested target event count, keep precise ticker/funding blockers or fail with `TICKER_COVERED_EVENT_COUNT_BELOW_TARGET`. Do not mark them available.
