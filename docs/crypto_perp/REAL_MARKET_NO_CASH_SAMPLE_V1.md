<!--
作成日: 2026-07-07_18:06 JST
更新日: 2026-07-08_07:20 JST
-->

# Crypto Perp Real-Market No-Cash Sample v1

## 結論

`crypto-perp-real-market-no-cash-sample` は、fixture-only dogfood ではなく public market candle source から no-cash event/outcome set を作る local CLI です。

この command は Paper Observation、paper order permission、profit proof、actual cash readiness、tiny-live readiness、live readiness を出しません。HOLD が出た場合でも、次に進めるのは human review for Paper Observation までです。

## CLI

既存 public source root から作る場合:

```bash
uv run sis crypto-perp-real-market-no-cash-sample \
  --source-root data/strategy_idea_candidates/btc-perp/bitget_public_source/source_root \
  --out data/crypto_perp/real_market_no_cash/latest
```

CSV projection から作る場合:

```bash
uv run sis crypto-perp-real-market-no-cash-sample \
  --input-csv data/crypto_perp/real_market_no_cash/latest/input/BTCUSDT_5m_public_market.csv \
  --out data/crypto_perp/real_market_no_cash/latest
```

forward-collected ticker rows が十分にある future event だけを選ぶ場合:

```bash
uv run sis crypto-perp-real-market-no-cash-sample \
  --source-root data/strategy_idea_candidates/btc-perp/bitget_public_source/source_root \
  --require-ticker-coverage \
  --ticker-max-staleness-seconds 900 \
  --out data/crypto_perp/real_market_no_cash/latest
```

ticker/funding source coverage を別の local source root から接続する場合:

```bash
uv run sis crypto-perp-real-market-no-cash-sample \
  --input-csv data/crypto_perp/real_market_no_cash/latest/input/BTCUSDT_5m_public_market.csv \
  --ticker-source-root data/strategy_idea_candidates/btc-perp/bitget_public_source/source_root \
  --ticker-max-staleness-seconds 900 \
  --out data/crypto_perp/real_market_no_cash/latest
```

`--source-root` を使う場合は、その source root 内の `data/ticker_rows` / `data/ticker_manifest.json` を ticker coverage 候補として、`data/funding_rows` / `data/funding_manifest.json` を funding coverage 候補として使います。`--source-root` と `--input-csv` を両方省略した場合は `data/strategy_idea_candidates/btc-perp/bitget_public_source/source_root` を使います。

作成後は fixture default と混ざらないよう、専用 `--data-dir` を渡します。

```bash
uv run sis crypto-perp-backtest-candidate-pack \
  --data-dir data/crypto_perp/real_market_no_cash/latest \
  --out data/crypto_perp/real_market_no_cash/backtest_candidate_pack/latest

uv run sis crypto-perp-no-cash-backtest-gate \
  --decision data/crypto_perp/real_market_no_cash/backtest_candidate_pack/latest/decision.json \
  --data-availability data/crypto_perp/real_market_no_cash/backtest_candidate_pack/latest/data_availability_ledger.json \
  --backtest data/crypto_perp/real_market_no_cash/backtest_candidate_pack/latest/backtest_result.json \
  --stress data/crypto_perp/real_market_no_cash/backtest_candidate_pack/latest/stress_result.json \
  --rolling-stability data/crypto_perp/real_market_no_cash/backtest_candidate_pack/latest/rolling_stability_result.json \
  --out data/crypto_perp/real_market_no_cash/no_cash_backtest_gate/latest
```

## Selection Policy

The default event selection policy is `time_evenly_spaced_before_outcome; no outcome-favorable filtering; require_ticker_coverage=false`.

The command selects eligible windows before evaluating the future outcome. It does not select only favorable outcomes, drop losing events, or replace `NO_TRADE` with a trade action. With `--require-ticker-coverage`, candidate windows are filtered before outcome construction to those whose `information_cutoff_at` already has timestamp-safe ticker bid/ask coverage. If fewer than the requested target count are covered, the command fails with `TICKER_COVERED_EVENT_COUNT_BELOW_TARGET` instead of silently using uncovered events.

## Expected Gaps

Current public candle-only runs can build 30+ matured event/outcome pairs and make PBO / rolling stability estimable. Ticker coverage is marked available only when a local public ticker row has `ts_received_ms <= information_cutoff_at`, is within `--ticker-max-staleness-seconds`, and includes valid `bid_px` / `ask_px`. A current ticker snapshot is not treated as if it existed before older event cutoffs. Historical price, mark, or index candles alone are not bid/ask ticker coverage.

`strategy-idea-candidates-bitget-source-refresh` records current Bitget REST ticker snapshots, historical market candles, and historical funding rows. `--append-existing` preserves existing parquet history and appends newly fetched ticker snapshots so future event cutoffs can become covered after time passes. A single append run normally does not clear old event cutoffs; ticker coverage is only usable when the saved row's `ts_received_ms` is at or before the event cutoff and within staleness bounds.

The refresh also records `CURRENT_TICKER_SNAPSHOT_ONLY`, `HISTORICAL_BID_ASK_TICKER_NOT_AVAILABLE_FROM_BITGET_PUBLIC_REST`, and `PRICE_MARK_INDEX_CANDLES_NOT_BID_ASK_TICKER_COVERAGE` so downstream review can see that public REST candles are not native historical bid/ask ticker rows. The relevant public docs are current ticker (`/api/v2/mix/market/ticker`), historical market candles (`/api/v2/mix/market/history-candles`), historical mark candles (`/api/v2/mix/market/history-mark-candles`), and historical index candles (`/api/v2/mix/market/history-index-candles`). None of those candle endpoints clear bid/ask ticker coverage by themselves.

Funding coverage is evaluated separately from ticker coverage. It is marked available only when a public historical funding row has `funding_time_ms <= information_cutoff_at`, `available_at_ms <= information_cutoff_at`, and a non-null `funding_rate`. If the source row is after the event cutoff, unavailable, missing bid/ask, or too stale, ticker/funding remain blockers instead of being zero-filled.

Expected known gaps can include:

- `PUBLIC_MARKET_CANDLES_ONLY`
- `HISTORICAL_TICKER_SOURCE_NOT_AVAILABLE`
- `HISTORICAL_TICKER_BID_ASK_NOT_AVAILABLE`
- `HISTORICAL_BID_ASK_TICKER_NOT_AVAILABLE_FROM_BITGET_PUBLIC_REST`
- `CURRENT_TICKER_SNAPSHOT_ONLY`
- `PRICE_MARK_INDEX_CANDLES_NOT_BID_ASK_TICKER_COVERAGE`
- `TICKER_COVERED_EVENT_COUNT_BELOW_TARGET`
- `FUNDING_SOURCE_MISSING_BEFORE_CUTOFF`
- `HISTORICAL_FUNDING_SOURCE_NOT_AVAILABLE`
- `BOOKS_SOURCE_MISSING`
- `TRADES_SOURCE_MISSING`
- `REPLAY_SOURCE_MISSING`
- `LOCAL_SIMULATION_ONLY`
- `NOT_ACTUAL_CASH`

## Boundary

The command does not use credentialed exchange APIs, wallet, signing, exchange write, paper order, live order, actual cash rows, or cash ledger. It does not zero-fill missing sources. It must not emit `DOGFOOD_FIXTURE_NOT_REAL_MARKET_EVIDENCE` in the real-market run.
