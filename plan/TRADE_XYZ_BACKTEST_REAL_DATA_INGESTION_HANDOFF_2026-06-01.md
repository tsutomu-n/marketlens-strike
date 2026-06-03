<!--
作成日: 2026-06-01_22:24 JST
更新日: 2026-06-03_19:17 JST
-->

# Trade[XYZ] Backtest Real Data Ingestion Handoff 2026-06-01

## 結論

この文書は、WS raw collection から backtest ingestion 実装へ渡すための受け渡しdraftである。
まだ実装開始readyではない。理由は、3symbol 24時間runのmanifestは生成済みで24時間完走したが、`unexpected_reconnect_count=1`、`error_count=1`、`quality status=warn` が残っているからである。

2026-06-02_19:01 JST に、server側の `1000 (OK) Expired` close を expected graceful reconnect として扱う修正を入れた。
2026-06-03_19:17 JST の24時間runでは、`graceful_reconnect_count=7`、`unexpected_reconnect_count=1` だった。

現時点でできるのは、次の境界を固定することだけである。

```text
できる:
  WS raw contractを説明する
  bbo / trades / activeAssetCtx の用途を分ける
  backtest ingestion前の禁止事項を固定する
  market_data.py / bar_builder.py に渡す前のタスクを列挙する

まだしない:
  market_data.py 実装変更
  bar_builder.py 実装変更
  run_backtest() 入力adapter実装
  no-lookahead testsの実装
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
  status: warn
  gap_count: 8
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
  reconnect_count == 0
  error_count == 0
  malformed_payload_count == 0
  unknown_symbol_count == 0
  bbo_bid_ask_inversion_count == 0
  REST parity status == pass

説明つき保留:
  gap_count > 0
  source_ts_gap_count > 0
  quality status == warn

data-ready禁止:
  unexpected_reconnect_count > 0 で欠損区間を説明できない
  error_count > 0
  REST parity status != pass
  day partitionが壊れている
```

## 次の実装タスク

24時間run完了後にだけ実行する。

```text
1. 24時間runのcapture / quality / REST parity manifestを確定する
2. このhandoffのReadiness Gateを実測値で更新する
3. WS raw -> normalized quote candidate の最小fixtureを作る
4. bboをfill snapshot候補へ変換するunit testを書く
5. activeAssetCtxをsignal/state候補へ変換するunit testを書く
6. recv_ts_msをoracle timestampにしないno-lookahead / provenance testを書く
7. market_data.py または新adapterの責務を決める
8. bar_builder.pyへ渡す前にsignal/fill splitを固定する
```

## 未完了理由

```text
3symbol 24時間run:
  完走。final manifest生成済み。

backtest ingestion code:
  unexpected_reconnect_count=1、error_count=1、quality status=warn のため、まだ変更しない。

data-ready:
  backtest_data_ready=false のまま。
```
