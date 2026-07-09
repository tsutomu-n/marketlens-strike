<!--
作成日: 2026-07-09_10:48 JST
更新日: 2026-07-09_15:14 JST
-->

# Crypto Perp Real-Market Ticker Coverage Status v1

## 結論

`crypto-perp-real-market-ticker-coverage-status` は、forward-collected ticker rows が no-cash gate 用の ticker-required sample に進めるだけ溜まっているかを読む local status CLI です。

この command は network を使わず、既存 local `source_root` の `candles_5m`、`ticker_rows`、`ticker_manifest.json`、`funding_rows` だけを読みます。Paper Observation、paper order permission、profit proof、actual cash readiness、live readiness は出しません。

## CLI

```bash
uv run sis crypto-perp-real-market-ticker-coverage-status \
  --source-root data/strategy_idea_candidates/btc-perp/bitget_public_source/source_root \
  --target-event-count 30 \
  --ticker-max-staleness-seconds 900 \
  --out data/crypto_perp/real_market_no_cash/ticker_coverage_status/latest
```

出力:

```text
data/crypto_perp/real_market_no_cash/ticker_coverage_status/latest/ticker_coverage_status.json
data/crypto_perp/real_market_no_cash/ticker_coverage_status/latest/ticker_coverage_status.md
```

## Decisions

- `READY_FOR_TICKER_REQUIRED_SAMPLE`: `ticker_covered_candidate_count >= target_event_count`。次は `crypto-perp-real-market-no-cash-sample --require-ticker-coverage`。
- `COLLECT_TICKER_SNAPSHOTS`: source root は読めるが、covered candidate が target 未満。次は public refresh の `--append-existing`。
- `SOURCE_ROOT_MISSING`: source root が存在しない。
- `NO_CANDLES`: candle rows がない、または lookback / horizon を満たす candidate window がない。
- `NO_TICKER_ROWS`: ticker parquet rows がない。

## Maturity Diagnostics

JSON / Markdown / stdout は、covered count だけでなく CP2 の未達理由を読むための診断を出します。

主要フィールド:

- `latest_candle_ts_ms`: local candle source の最新 candle timestamp。
- `latest_matured_event_cutoff_ms`: default horizon を満たす最新 event cutoff。
- `earliest_ticker_ts_received_ms` / `latest_ticker_ts_received_ms`: 保存済み ticker snapshot の受信範囲。
- `matured_ticker_row_count`: latest matured event cutoff 以前にある bid/ask 付き ticker rows。
- `future_unmatured_ticker_row_count`: ticker row はあるが、horizon がまだ成熟していない future-side rows。
- `coverage_shortfall`: `target_event_count - ticker_covered_candidate_count`。
- `next_maturity_hint`: 最新 ticker が 60 分 horizon を満たすために必要な candle timestamp と残秒数。
- `diagnosis`: 次にやるべきことを1つに寄せた分類。

`diagnosis` の意味:

- `COLLECT_MORE_TICKER_ROWS`: bid/ask 付き ticker rows が target に足りない。
- `WAIT_FOR_HORIZON_MATURITY`: ticker rows はあるが、candidate/outcome horizon がまだ成熟していない。
- `CANDLES_NOT_ADVANCING`: ticker より candle source が遅れている。
- `TICKER_ROWS_STALE`: ticker rows はあるが staleness threshold を超えている。
- `READY_FOR_TICKER_REQUIRED_SAMPLE`: `crypto-perp-real-market-no-cash-sample --require-ticker-coverage` に進める。

## Operational Reality

1 回の `--append-existing` は、古い event cutoff を retroactively clear しません。current ticker snapshot は、保存された `ts_received_ms` 以後の future event cutoff にだけ使えます。

default は 5 分足、lookback 60 分、horizon 60 分、ticker staleness 900 秒です。30 covered candidates を作るには、複数回の forward ticker snapshot collection と、outcome が成熟するための horizon 待ちが必要です。

実務上は、5 分間隔で public refresh を繰り返し、そのたびにこの status CLI を再実行します。`READY_FOR_TICKER_REQUIRED_SAMPLE` が出るまでは、ticker-required sample、backtest candidate pack、no-cash gate へ進みません。

48 回、約 4 時間の collection 後も target 未満なら、無理に gate へ進まず `missing_reason_counts` で原因を 1 class に絞ります。

- `valid_bid_ask_row_count` が増えない: refresh / merge / source 品質の問題。
- `TICKER_SOURCE_STALE` が増える: collection cadence または timestamp 整合の問題。
- `HISTORICAL_TICKER_BID_ASK_NOT_AVAILABLE` が出る: bid/ask 欠落 source 品質の問題。
- valid rows は増えるが covered candidates が増えない: horizon 未成熟または candidate window 整合の問題。

## Boundary

coverage 判定は既存の `build_ticker_source_status` を使います。current ticker snapshot を古い event cutoff に流用せず、market / mark / index candles を bid/ask ticker coverage として扱いません。

status が ready になっても Paper Observation には進みません。次は ticker-required sample、backtest candidate pack、no-cash gate の順で再実行します。
