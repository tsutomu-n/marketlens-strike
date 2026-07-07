<!--
作成日: 2026-07-07_19:12 JST
更新日: 2026-07-07_19:12 JST
-->

# Issue 29 Ticker/Funding Source Coverage Plan

## Checkpoint

CP2: connect ticker/funding coverage to the real-market no-cash sample path when public/local source evidence exists.

## Purpose

Remove `CRITICAL_SIGNAL_SOURCE_MISSING_TICKER` and `CRITICAL_SIGNAL_SOURCE_MISSING_FUNDING` only when source rows are timestamp-safe for each event cutoff.

## Constraints

No credentialed API, wallet/signing, exchange write, paper/live order, actual cash rows, profit proof, zero-filled ticker/funding, fabricated funding, dropped losing events, or manual `NO_TRADE` override.

## Target Files

- `src/sis/crypto_perp/ticker_source.py`
- `src/sis/crypto_perp/real_market_no_cash_sample.py`
- `src/sis/commands/crypto_perp_real_market_no_cash_sample.py`
- `tests/crypto_perp/test_real_market_no_cash_sample.py`
- `docs/crypto_perp/REAL_MARKET_NO_CASH_SAMPLE_V1.md`

## Implementation

Use existing `build_ticker_source_status` to select the latest ticker row with `ts_received_ms <= information_cutoff_at`. Attach ticker source coverage when it is available and not stale. Attach funding coverage from the same selected row only when `funding_rate` is present. Leave books/trades/replay as known gaps.

## Tests

Add a deterministic local ticker source root fixture. Verify ticker/funding blockers disappear when rows are valid, and remain absent from real-market fixture markers. Run focused tests, docs checks, CLI catalog check, `git diff --check`, and `./scripts/check`.

## Failure Conditions

If public source rows are after event cutoffs or stale, keep precise ticker/funding blockers. Do not mark them available.
