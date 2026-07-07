<!--
作成日: 2026-07-07_19:12 JST
更新日: 2026-07-07_20:05 JST
-->

# Issue 29 Ticker/Funding Source Coverage Plan

## Checkpoint

CP3: connect historical/cutoff-before funding coverage and keep ticker coverage timestamp-safe for the real-market no-cash sample path.

## Purpose

Remove `CRITICAL_SIGNAL_SOURCE_MISSING_FUNDING` when historical public funding rows are timestamp-safe for each event cutoff. Remove ticker blockers only when native ticker rows are also timestamp-safe; do not use a current ticker snapshot for older event cutoffs.

## Constraints

No credentialed API, wallet/signing, exchange write, paper/live order, actual cash rows, profit proof, zero-filled ticker/funding, fabricated funding, dropped losing events, or manual `NO_TRADE` override.

## Target Files

- `src/sis/crypto_perp/ticker_source.py`
- `src/sis/crypto_perp/funding_source.py`
- `src/sis/crypto_perp/real_market_no_cash_sample.py`
- `src/sis/strategy_idea_candidates/bitget_public_source.py`
- `src/sis/commands/crypto_perp_real_market_no_cash_sample.py`
- `tests/crypto_perp/test_real_market_no_cash_sample.py`
- `docs/crypto_perp/REAL_MARKET_NO_CASH_SAMPLE_V1.md`

## Implementation

Use existing `build_ticker_source_status` to select the latest ticker row with `ts_received_ms <= information_cutoff_at`. Add `build_funding_source_status` for `data/funding_rows`, selecting only rows with `funding_time_ms <= information_cutoff_at`, `available_at_ms <= information_cutoff_at`, and non-null `funding_rate`. Attach ticker and funding coverage independently. If only a fresh ticker snapshot exists, keep ticker blocked as `HISTORICAL_TICKER_SOURCE_NOT_AVAILABLE`; do not derive ticker from candles. Leave books/trades/replay as known gaps.

## Tests

Add deterministic local ticker and funding source root fixtures. Verify funding blockers disappear when historical funding rows are valid, ticker blockers disappear only when native ticker rows are valid, and fixture markers remain absent from real-market artifacts. Run focused tests, docs checks, CLI catalog check, `git diff --check`, and `./scripts/check`.

## Failure Conditions

If public source rows are after event cutoffs or stale, keep precise ticker/funding blockers. Do not mark them available.
