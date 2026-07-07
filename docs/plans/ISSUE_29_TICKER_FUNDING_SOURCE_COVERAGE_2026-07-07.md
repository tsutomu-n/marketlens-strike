<!--
作成日: 2026-07-07_19:12 JST
更新日: 2026-07-07_20:45 JST
-->

# Issue 29 Ticker/Funding Source Coverage Plan

## Checkpoint

CP4: require bid/ask-backed historical ticker coverage and keep current ticker snapshots out of old event cutoffs.

## Purpose

Remove ticker blockers only when native ticker rows are timestamp-safe and include bid/ask. Historical price, mark, or index candles alone do not clear ticker coverage. Funding remains independent through the historical funding rows from PR #31.

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

Use `build_ticker_source_status` to select the latest valid ticker row with `ts_received_ms <= information_cutoff_at`, valid `bid_px`, and valid `ask_px`. If only a fresh ticker snapshot exists, keep ticker blocked as `HISTORICAL_TICKER_SOURCE_NOT_AVAILABLE`. If historical rows exist but lack bid/ask, keep ticker blocked as `HISTORICAL_TICKER_BID_ASK_NOT_AVAILABLE`. Do not derive ticker coverage from candles. Keep funding independent through `build_funding_source_status`. Leave books/trades/replay as known gaps.

## Tests

Add deterministic local ticker and funding source root fixtures. Verify ticker blockers disappear only when native ticker rows have timestamp-safe bid/ask, funding stays available when ticker remains blocked, and fixture markers remain absent from real-market artifacts. Run focused tests, docs checks, CLI catalog check, `git diff --check`, and `./scripts/check`.

## Failure Conditions

If public source rows are after event cutoffs or stale, keep precise ticker/funding blockers. Do not mark them available.
