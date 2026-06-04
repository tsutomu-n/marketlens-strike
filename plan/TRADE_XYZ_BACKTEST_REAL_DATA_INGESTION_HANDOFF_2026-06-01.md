<!--
作成日: 2026-06-01_22:24 JST
更新日: 2026-06-04_16:49 JST
-->

# Trade[XYZ] Backtest Real Data Ingestion Handoff 2026-06-01

## 結論

この文書は、WS raw collection から backtest ingestion 実装へ渡すための受け渡しdraftである。
WS取得基盤としては実装開始readyである。3symbol 24時間runは完走し、final quality manifest は `status=pass`、REST parity も `status=pass` である。

ただし、これは `backtest_data_ready=true` ではない。現在の strict fail は長期quote coverageで、oracle timestamp provenance は known gap として別gateに残る。`real_market_reference` は現在の readiness manifest では pass である。

2026-06-02_19:01 JST に、server側の `1000 (OK) Expired` close を expected graceful reconnect として扱う修正を入れた。
2026-06-03_19:17 JST の24時間runでは、`graceful_reconnect_count=7`、`unexpected_reconnect_count=1` だった。
2026-06-03_19:35 JST に、control subscriptionResponse gapをmarket data quality warnから除外してmanifestを再生成した。
`unexpected_reconnect_count=1` は約1.074秒のtransport reconnectで、60秒超のquote/state gapを作っていないため、T10では受容する。
2026-06-03_19:37 JST に `./scripts/check` がpassし、pytestは794件passした。
2026-06-04_06:39 JST に、WS raw rowを `QuoteLog` へ変換する最小adapterを追加した。
`bbo` は fill snapshot候補、`activeAssetCtx` は signal/state候補として分離し、`recv_ts_ms` を oracle timestamp として使わない回帰テストを追加した。
2026-06-04_06:47 JST に、WS raw JSONL から normalized parquet / DuckDB を出力するCLIを追加し、24時間runの isolated raw root で 1,113,529 行の正規化を確認した。
2026-06-04_06:56 JST に、artifact manifest出力、BBO barへのactiveAssetCtx no-lookahead asof join、run_backtest最小smokeを追加した。
2026-06-04_06:58 JST に `./scripts/check` がpassし、pytestは801件passした。
2026-06-04_16:39 JST に、signal candle manifest の `request_error_count=5` を read-only 再収集で解消した。
`trade_xyz_signal_candles_manifest.json` は `row_count=67765`、`symbol_count=11`、`request_error_count=0` で、collection status上も `signal_candles_status=pass` になった。
残るstrict failは `quote_coverage` だけで、coverageが30日要件に届くまで継続収集が必要である。
2026-06-04_16:39 JST 時点で、次の24時間read-only data cycleを起動済みである: PID `2484910`、log `logs/trade_xyz_data_cycle/trade_xyz_data_cycle_20260604_073932.log`。
2026-06-04_16:48 JST に、同種の 429 rate limit error を再発させにくくするため、signal candle collectorのdefault delayを `1.5` 秒へ変更し、readiness next action と runbook も同じ値へ更新した。

現時点でできるのは、次の境界を固定することだけである。

```text
できる:
  WS raw contractを説明する
  bbo / trades / activeAssetCtx の用途を分ける
  backtest ingestion前の禁止事項を固定する
  market_data.py / bar_builder.py に渡す前のタスクを列挙する

まだしない:
  backtest_data_ready=true 宣言
```

## 正本

実装時は、次の順で確認する。

```text
1. schemas/trade_xyz_ws_raw.v1.schema.json
2. schemas/trade_xyz_ws_capture_manifest.v1.schema.json
3. schemas/trade_xyz_ws_quality_manifest.v1.schema.json
4. schemas/trade_xyz_rest_parity_manifest.v1.schema.json
5. src/sis/venues/trade_xyz/ws_envelope.py
6. src/sis/venues/trade_xyz/ws_recorder.py
7. src/sis/venues/trade_xyz/ws_quality.py
8. tests/test_trade_xyz_ws_*.py
9. data/manifests/*.json
10. docs/TRADE_XYZ_REAL_DATA_COLLECTION_CURRENT_RECORD_2026-06-01.md
11. docs/集めるべき実データ0531-2108/README.md
12. plan/TRADE_XYZ_BACKTEST_V0_1_2_REAL_DATA_HARDENING_PLAN_REV5.md
```

## WS Raw Contract

保存先:

```text
data/raw/ws/trade_xyz/
```

partition:

```text
date=<YYYY-MM-DD>/subscription=<subscription>/symbol=<canonical_symbol>/part-000001.jsonl
```

raw row schema:

```text
schema_version: trade_xyz_ws_raw.v1
source: hyperliquid_ws
source_tier: official_ws
dex: xyz
ws_url: wss://api.hyperliquid.xyz/ws
channel
message_kind
subscription
subscription_hash
connection_id
sequence
recv_ts_ms
recv_monotonic_ns
payload_sha256
payload
```

任意field:

```text
source_ts_ms
source_ts_field
canonical_symbol
venue_symbol
coin
is_snapshot
```

`recv_ts_ms` は受信時刻であり、source/oracle timestampではない。

## Subscription別の用途

### bbo

用途:

```text
fill snapshot candidate
quote coverage candidate
spread / bid-ask inversion quality check
```

主なpayload:

```text
payload.data.coin
payload.data.time
payload.data.bbo[0].px
payload.data.bbo[0].sz
payload.data.bbo[1].px
payload.data.bbo[1].sz
```

timestamp:

```text
source_ts_ms:
  payload.data.time から取得可能

event_ts候補:
  source_ts_ms を使えるが、recv_ts_msとは分ける
```

backtest側へ渡す前に決めること:

```text
best_bid = bbo[0].px
best_ask = bbo[1].px
mid_price = (best_bid + best_ask) / 2
spread_bps = (best_ask - best_bid) / mid_price * 10000
```

### trades

用途:

```text
trade tape
liquidity / activity reference
```

注意:

```text
trade_gap_count は低流動により自然に増える。
trade_gap_count 単独で quote coverage fail とみなさない。
trades を fill snapshot の正本にしない。
```

timestamp:

```text
source_ts_ms:
  trades.data[].time が単一値として解決できる場合のみ扱う
```

### activeAssetCtx

用途:

```text
mark/oracle/mid/funding/openInterest reference
state snapshot
```

主なpayload:

```text
payload.data.ctx.funding
payload.data.ctx.openInterest
payload.data.ctx.prevDayPx
payload.data.ctx.dayNtlVlm
payload.data.ctx.premium
payload.data.ctx.oraclePx
payload.data.ctx.markPx
payload.data.ctx.midPx
payload.data.ctx.impactPxs
payload.data.ctx.dayBaseVlm
```

timestamp:

```text
source_ts_ms:
  現payloadでは明示source timestampがない

recv_ts_ms:
  受信時刻としてだけ使う
```

禁止:

```text
recv_ts_ms を oracle timestamp として扱わない
oraclePx があることを oracle timestamp provenance 解決とみなさない
```

## Signal / Fill 分離

ingestion adapter は、次を混ぜない。

```text
signal fields:
  戦略が見る価格・状態

fill snapshot fields:
  仮想約定が見るbid/ask/spread/fee/gate状態
```

推奨初期方針:

```text
signal:
  activeAssetCtx.midPx または bbo mid_price を候補にする

fill:
  bbo best_bid / best_ask を候補にする

event_ts:
  source_ts_ms がある bbo は source_ts_ms を候補にする
  source_ts_ms がない activeAssetCtx は recv_ts_ms を source時刻として使わない
```

実装済みadapter:

```text
src/sis/venues/trade_xyz/normalizer.py:
  quote_from_ws_bbo_row(row, ...)
    source: trade_xyz_ws_bbo
    role: fill snapshot candidate
    preserves: recv_ts_ms, source_ts_ms, payload_sha256/raw_payload
    sets: best_bid, best_ask, mid_price, spread_bps, exec_buy_price, exec_sell_price

  quote_from_ws_active_asset_ctx_row(row)
    source: trade_xyz_ws_activeAssetCtx
    role: signal/state candidate
    preserves: recv_ts_ms, payload_sha256/raw_payload
    sets: mark_price, oracle_price, index_price, mid_price, funding_rate, open_interest_usd
    does not set: best_bid, best_ask, exec_buy_price, exec_sell_price
    block_reasons: [BLOCK_NO_BBO_FILL_SNAPSHOT]
```

実装済みdataset builder:

```text
src/sis/storage/normalize.py:
  normalize_trade_xyz_ws_quotes(raw_ws_root, parquet_path, duckdb_path, ...)

src/sis/commands/quotes.py:
  uv run sis normalize-trade-xyz-ws-quotes \
    --raw-ws-root data/raw/ws/trade_xyz_24h_20260602_1902 \
    --parquet-path .tmp/trade_xyz_ws_quotes_24h.parquet \
    --duckdb-path .tmp/trade_xyz_ws_quotes_24h.duckdb \
    --manifest-path .tmp/trade_xyz_ws_quotes_24h.manifest.json \
    --quality-manifest-path data/manifests/trade_xyz_ws_quality_manifest.json \
    --rest-parity-manifest-path data/manifests/trade_xyz_rest_parity_manifest.json \
    --registry-path data/registry/trade_xyz_instrument_registry.json \
    --symbols SP500,XYZ100,NVDA

src/sis/backtest/trade_xyz/ws_ingestion.py:
  build_bbo_bars_with_active_asset_state(frame, ...)
```

実データ確認:

```text
normalized_rows: 1113529
sources:
  trade_xyz_ws_activeAssetCtx: 251670
  trade_xyz_ws_bbo: 861859
symbols:
  NVDA: 351870
  SP500: 298738
  XYZ100: 462921
oracle_ts_non_null: 0
active_tradable_rows: 0
bbo_missing_bid: 0
bbo_missing_ask: 0
output:
  .tmp/trade_xyz_ws_quotes_24h.parquet: 140M
  .tmp/trade_xyz_ws_quotes_24h.duckdb: 273M
  .tmp/trade_xyz_ws_quotes_24h.manifest.json: 1.6K
max_rss: 2458468 KB
elapsed: 50.88s
manifest:
  row_count_raw_seen: 1202996
  quote_count_written: 1113529
  bbo_quote_count: 861859
  active_asset_ctx_quote_count: 251670
  trade_row_count_skipped: 89383
  control_row_count_skipped: 81
  duplicate_count_skipped: 3
  malformed_count: 0
```

backtest接続確認:

```text
normalize_trade_xyz_market_data:
  SP500 bbo sample 1000 rows pass

prepare_quote_rows_for_backtest:
  event_time_source=source_ts_ms, close_source=mid_price pass

build_quote_bars:
  SP500 bbo sample 10000 rows -> 1h bars 2 rows
  exec_buy_price / exec_sell_price / fill_best_bid / fill_best_ask nullなし

build_bbo_bars_with_active_asset_state:
  SP500 sample 20000 rows -> 1h bars 3 rows
  state_mark_price / state_observed_ts_ms / fill_best_bid / fill_best_ask nullなし

run_backtest:
  BBO-only fixture pass
```

broad verification:

```text
./scripts/check:
  pass
  pytest: 801 passed in 21.93s
```

adapter境界:

```text
bbo:
  fill snapshot 候補として tradable 判定できる
  oracle_ts_ms は asset_ctx が無いので missing

activeAssetCtx:
  mark/oracle/funding/openInterest を持つが、fill snapshot ではない
  source_ts_ms が無いraw rowでは source_ts_ms=None のまま
  recv_ts_ms を oracle_ts_ms に流用しない
```

## Readiness Gate

次を満たすまで backtest ingestion 実装へ進めない。

```text
1. 3symbol 24時間runのcapture manifestがある
2. 3symbol 24時間runのquality manifestがある
3. 3symbol 24時間runのREST parity manifestがある
4. reconnect_count / error_count / gap_count が説明できる
5. day partitionが壊れていない
6. raw_pathsが data/raw/ws/trade_xyz/ のWS partitionを指す
7. 2026-05-30以前のarchiveを参照していない
8. allMidsをdex=xyz未確認のまま正本にしていない
9. l2BookをL2 replayやfill modelへ接続していない
10. Current Real Data Contractが最新化されている
```

## 24時間run完了後に更新する欄

この欄は、`data/raw/ws/trade_xyz_24h_20260602_1902/` の24時間runが終了してからだけ埋める。
途中snapshotで埋めない。

```text
capture_manifest:
  path: data/manifests/trade_xyz_ws_capture_manifest.json
  started_at: 2026-06-02T10:03:22.093603+00:00
  ended_at: 2026-06-03T10:03:23.295834+00:00
  duration_seconds: 86401.202231
  row_count: 1202996
  bytes_written: 1133437251
  connection_count: 9
  reconnect_count: 8
  graceful_reconnect_count: 7
  unexpected_reconnect_count: 1
  error_count: 1
  subscription_response_count: 81

quality_manifest:
  path: data/manifests/trade_xyz_ws_quality_manifest.json
  status: pass
  gap_count: 0
  source_ts_gap_count: 0
  trade_gap_count: 35
  malformed_payload_count: 0
  unknown_symbol_count: 0
  bbo_bid_ask_inversion_count: 0

rest_parity_manifest:
  path: data/manifests/trade_xyz_rest_parity_manifest.json
  status: pass
  missing_ws_symbols: []
  missing_rest_symbols: []
  mismatched_symbols: []

disk_usage:
  data/raw/ws/trade_xyz_24h_20260602_1902/: 1.1G

day_partition:
  status: pass. raw_paths are under data/raw/ws/trade_xyz_24h_20260602_1902/date=2026-06-02 and date=2026-06-03 partitions.
```

完了後の最小コマンド:

```bash
uv run sis build-trade-xyz-ws-quality \
  --raw-ws-root data/raw/ws/trade_xyz \
  --recv-gap-threshold-seconds 60 \
  --source-gap-threshold-seconds 60

uv run sis build-trade-xyz-rest-parity \
  --symbols SP500,XYZ100,NVDA \
  --ws-manifest-path data/manifests/trade_xyz_ws_capture_manifest.json \
  --request-delay-seconds 0.2 \
  --skip-l2-book

du -sh data/raw/ws/trade_xyz
```

判定:

```text
pass候補:
  unexpected reconnect があっても、60秒超のquote/state gapを作らず、原因と影響範囲が記録されている
  malformed_payload_count == 0
  unknown_symbol_count == 0
  bbo_bid_ask_inversion_count == 0
  REST parity status == pass

説明つき保留:
  market data gap_count > 0
  source_ts_gap_count > 0
  quality status == warn/fail

data-ready禁止:
  unexpected_reconnect_count > 0 で欠損区間を説明できない
  error_count > 0 で市場データ欠損への影響を説明できない
  REST parity status != pass
  day partitionが壊れている
```

## 次の実装タスク

24時間run完了後にだけ実行する。

```text
1. DONE: 24時間runのcapture / quality / REST parity manifestを確定する
2. DONE: このhandoffのReadiness Gateを実測値で更新する
3. DONE: WS raw -> normalized quote candidate の最小fixtureを作る
4. DONE: bboをfill snapshot候補へ変換するunit testを書く
5. DONE: activeAssetCtxをsignal/state候補へ変換するunit testを書く
6. DONE: recv_ts_msをoracle timestampにしないno-lookahead / provenance testを書く
7. DONE: market_data.py または新adapterの責務を決める
8. DONE: bar_builder.pyへ渡す前にsignal/fill splitを固定する
```

## 未完了理由

```text
3symbol 24時間run:
  完走。final manifest生成済み。quality / REST parity はpass。

backtest ingestion code:
  最小normalizer adapterとWS raw JSONL -> normalized parquet/DuckDB builderは実装済み。
  market_data.py / bar_builder.py への最小接続も確認済み。
  ただし、WS raw contractとsignal/fill splitを守り、recv_ts_msをoracle timestampとして使わない。

data-ready:
  backtest_data_ready=false のまま。
```

## 2026-06-04_16:39 JST の broader readiness 状態

すぐ潰せるエラー:

```text
signal_candles_request_error_count:
  before: 5
  after: 0

signal_candles_status:
  pass
```

実行したコマンド:

```bash
uv run sis collect-trade-xyz-signal-candles \
  --registry-path data/registry/trade_xyz_instrument_registry.json \
  --intervals 30m,4h,1d,3d \
  --period-days 365 \
  --request-delay-seconds 1.5

uv run sis build-trade-xyz-data-readiness --strict
uv run sis trade-xyz-collection-status --no-refresh-coverage --refresh-readiness --strict
```

残るfail:

```text
failing_requirements: quote_coverage
known_gap_requirements: oracle_timestamp_provenance
estimated_max_collection_days_required: 29
backtest_data_ready: False
```

起動中collector:

```text
pid: 2484910
duration_minutes: 1440
interval_seconds: 60
symbols: AAPL,AMD,AMZN,EWJ,GOOGL,META,MSFT,NVDA,SP500,TSLA,XYZ100
skip_signal_candles: true
log_path: logs/trade_xyz_data_cycle/trade_xyz_data_cycle_20260604_073932.log
launcher_log: .tmp/launchers/trade_xyz_data_cycle_20260604_073932.setsid.log
```

再開時の確認:

```bash
ps -fp 2484910
tail -80 logs/trade_xyz_data_cycle/trade_xyz_data_cycle_20260604_073932.log
uv run sis trade-xyz-collection-status --no-refresh-coverage --refresh-readiness --strict
```

再発防止:

```text
collect-trade-xyz-signal-candles default --request-delay-seconds:
  1.5

readiness next_action:
  includes --request-delay-seconds 1.5

focused verification:
  uv run pytest -q tests/test_trade_xyz_candles.py
  5 passed
```
