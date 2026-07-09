<!--
作成日: 2026-07-09_10:48 JST
更新日: 2026-07-09_10:48 JST
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

## Boundary

coverage 判定は既存の `build_ticker_source_status` を使います。current ticker snapshot を古い event cutoff に流用せず、market / mark / index candles を bid/ask ticker coverage として扱いません。

status が ready になっても Paper Observation には進みません。次は ticker-required sample、backtest candidate pack、no-cash gate の順で再実行します。
