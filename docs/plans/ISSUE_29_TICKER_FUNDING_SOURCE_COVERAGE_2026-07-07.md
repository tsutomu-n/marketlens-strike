<!--
作成日: 2026-07-07_19:12 JST
更新日: 2026-07-08_07:20 JST
-->

# Issue 29 Ticker/Funding Source Coverage Plan

## Checkpoint

CP6: forward-collect public ticker snapshots and select only ticker-covered future no-cash event windows when requested.

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

Use `build_ticker_source_status` to select the latest valid ticker row with `ts_received_ms <= information_cutoff_at`, valid `bid_px`, and valid `ask_px`. Add `--append-existing` to `strategy-idea-candidates-bitget-source-refresh` so repeated public refreshes preserve ticker row history instead of replacing it. Add `--require-ticker-coverage` to `crypto-perp-real-market-no-cash-sample` so selected event windows can be restricted to timestamp-safe ticker-covered cutoffs. If covered candidate windows are below target, fail with `TICKER_COVERED_EVENT_COUNT_BELOW_TARGET`. Keep funding independent through `build_funding_source_status`. Leave books/trades/replay as known gaps.

## Tests

Add deterministic append-mode and local ticker/funding fixtures. Verify append preserves forward ticker snapshots, replace clears history, append+replace is rejected, `--require-ticker-coverage` filters uncovered windows, insufficient covered windows fail precisely, funding stays independent, and fixture markers remain absent. Run focused tests, docs checks, CLI catalog check, `git diff --check`, and `./scripts/check`.

## Failure Conditions

If public source rows are after event cutoffs, stale, or too sparse for the requested target event count, keep precise ticker/funding blockers or fail with `TICKER_COVERED_EVENT_COUNT_BELOW_TARGET`. Do not mark them available.
