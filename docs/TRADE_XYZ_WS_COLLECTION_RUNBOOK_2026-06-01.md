<!--
作成日: 2026-06-01_19:56 JST
更新日: 2026-06-01_19:56 JST
-->

# Trade[XYZ] WS Collection Runbook

更新日: 2026-06-01_19:56 JST

このrunbookは、Trade[XYZ]公式WebSocketのread-only captureを再実行するための手順である。
wallet、signing、private key、exchange write、live orderは不要であり、使わない。

## 前提

正本:

```text
registry:
  data/registry/trade_xyz_instrument_registry.json

config:
  configs/trade_xyz_data_collection.yaml

WS raw default:
  data/raw/ws/trade_xyz/

temporary smoke roots:
  .tmp/trade_xyz_ws_smoke_multi_symbol_<timestamp>/
  .tmp/trade_xyz_ws_smoke_15m_<timestamp>/
  .tmp/trade_xyz_ws_smoke_60m_<timestamp>/
  .tmp/trade_xyz_ws_smoke_11symbols_60m_<timestamp>/

manifests:
  data/manifests/trade_xyz_ws_capture_manifest.json
  data/manifests/trade_xyz_ws_quality_manifest.json
  data/manifests/trade_xyz_rest_parity_manifest.json
```

`data/manifests/*.json` は最新runで上書きされる。
複数runを比較する場合は、出力root名とチャットではなく current record docs に実値を残す。

## Dry Run

```bash
uv run sis collect-trade-xyz-ws \
  --registry-path data/registry/trade_xyz_instrument_registry.json \
  --symbols SP500,XYZ100,NVDA \
  --subscriptions bbo,trades,activeAssetCtx \
  --duration-minutes 1 \
  --output-dir .tmp/trade_xyz_ws_dry_run \
  --write-control-messages \
  --dry-run
```

確認:

```bash
uv run sis collect-trade-xyz-ws --help
```

## 1分 Smoke

```bash
uv run sis collect-trade-xyz-ws \
  --registry-path data/registry/trade_xyz_instrument_registry.json \
  --symbols SP500,XYZ100,NVDA \
  --subscriptions bbo,trades,activeAssetCtx \
  --duration-minutes 1 \
  --output-dir .tmp/trade_xyz_ws_smoke_multi_symbol_$(date +%Y%m%d_%H%M) \
  --write-control-messages
```

## 15分 Smoke

```bash
uv run sis collect-trade-xyz-ws \
  --registry-path data/registry/trade_xyz_instrument_registry.json \
  --symbols SP500,XYZ100,NVDA \
  --subscriptions bbo,trades,activeAssetCtx \
  --duration-minutes 15 \
  --output-dir .tmp/trade_xyz_ws_smoke_15m_$(date +%Y%m%d_%H%M) \
  --write-control-messages
```

## 60分 Capture

```bash
uv run sis collect-trade-xyz-ws \
  --registry-path data/registry/trade_xyz_instrument_registry.json \
  --symbols SP500,XYZ100,NVDA \
  --subscriptions bbo,trades,activeAssetCtx \
  --duration-minutes 60 \
  --output-dir .tmp/trade_xyz_ws_smoke_60m_$(date +%Y%m%d_%H%M) \
  --write-control-messages
```

## 11symbol 60分 Capture

```bash
uv run sis collect-trade-xyz-ws \
  --registry-path data/registry/trade_xyz_instrument_registry.json \
  --symbols SP500,XYZ100,NVDA,AAPL,MSFT,AMZN,GOOGL,META,TSLA,AMD,EWJ \
  --subscriptions bbo,trades,activeAssetCtx \
  --duration-minutes 60 \
  --output-dir .tmp/trade_xyz_ws_smoke_11symbols_60m_$(date +%Y%m%d_%H%M) \
  --write-control-messages
```

## Quality Check

`--raw-ws-root` は直前の capture output root に合わせる。

```bash
uv run sis build-trade-xyz-ws-quality \
  --raw-ws-root .tmp/trade_xyz_ws_smoke_60m_YYYYMMDD_HHMM \
  --recv-gap-threshold-seconds 60 \
  --source-gap-threshold-seconds 60

jq '{status,row_count,pong_count,gap_count,source_ts_gap_count,malformed_payload_count,unknown_symbol_count,bbo_bid_ask_inversion_count,duplicate_payload_count,subscription_counts,symbol_counts}' \
  data/manifests/trade_xyz_ws_quality_manifest.json
```

Pass目安:

```text
status: pass
gap_count: 0
source_ts_gap_count: 0
malformed_payload_count: 0
unknown_symbol_count: 0
bbo_bid_ask_inversion_count: 0
```

`duplicate_payload_count` は activeAssetCtx の同値再送を含む観測値であり、単独では warn / fail にしない。

## REST Parity Check

```bash
uv run sis build-trade-xyz-rest-parity \
  --symbols SP500,XYZ100,NVDA \
  --ws-manifest-path data/manifests/trade_xyz_ws_capture_manifest.json \
  --request-delay-seconds 0.2 \
  --skip-l2-book

jq '{status,request_error_count,missing_ws_symbols,missing_rest_symbols,mismatched_symbols,known_gap_count}' \
  data/manifests/trade_xyz_rest_parity_manifest.json
```

11symbol runでは `--symbols` を11symbolのCSVへ変える。

Pass目安:

```text
status: pass
request_error_count: 0
missing_ws_symbols: []
missing_rest_symbols: []
mismatched_symbols: []
known_gap_count: 0
```

## Capture Manifest Check

```bash
jq '{row_count,bytes_written,connection_count,reconnect_count,error_count,heartbeat_sent_count,pong_count,subscription_response_count,raw_paths}' \
  data/manifests/trade_xyz_ws_capture_manifest.json
```

Pass目安:

```text
connection_count: 1
reconnect_count: 0
error_count: 0
subscription_response_count: symbol_count * subscription_count
raw_paths: subscription and symbol partition paths exist
```

低流動channelでは、`heartbeat_sent_count` と `pong_count` が増えることがある。
高頻度にmessageが届くrunでは、どちらも `0` でも異常とは限らない。

## Disk Usage Check

```bash
du -sh .tmp/trade_xyz_ws_smoke_60m_YYYYMMDD_HHMM
```

結果は current record docs に残す。
保存量が想定を大きく超える場合は、60分以上や11symbolへ進めない。

## Fail時の調査順

1. `data/manifests/trade_xyz_ws_capture_manifest.json` の `error_count`, `reconnect_count`, `block_reasons` を見る。
2. `data/manifests/trade_xyz_ws_quality_manifest.json` の `block_reasons`, `unknown_symbol_count`, `malformed_payload_count`, `gap_count`, `source_ts_gap_count` を見る。
3. `data/manifests/trade_xyz_rest_parity_manifest.json` の `missing_ws_symbols`, `missing_rest_symbols`, `mismatched_symbols` を見る。
4. `find <output-root> -type f | sort` で partition を見る。
5. 必要なら raw JSONL の先頭数行だけを見る。

## 停止条件

次のどれかが出たら、次の長時間runへ進まない。

```text
reconnect_count > 0
error_count > 0
unknown_symbol_count > 0
malformed_payload_count > 0
bbo_bid_ask_inversion_count > 0
gap_count > 0 を説明できない
source_ts_gap_count > 0 を説明できない
REST parity が warn / fail
subscriptionResponse が symbol_count * subscription_count より少ない
symbol別partitionが作られない
保存量が運用不能
```

## Data-readyにしてはいけない条件

```text
3symbol 24時間runが未完了
11symbol 60分runが未完了
reconnect_count > 0 の欠損区間を説明できない
2026-05-30以前の実データを参照している
recv_ts_msをsource/oracle timestamp扱いしている
allMidsをdex=xyz未確認のまま正本にしている
l2BookをL2 replayやfill modelへ接続している
external referenceをTrade[XYZ]価格穴埋めに使っている
Current Real Data Contractが未更新
```
