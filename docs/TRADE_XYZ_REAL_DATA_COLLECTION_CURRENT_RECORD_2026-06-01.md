<!--
作成日: 2026-06-01_15:03 JST
更新日: 2026-06-01_20:54 JST
-->

# Trade[XYZ] Real Data Collection Current Record

更新日: 2026-06-01_20:54 JST

この文書は、第三者が `marketlens-strike` の現在状態を引き継ぐための記録である。コード、設定、生成済みartifactを正として書く。

## 0. 追加実装（2026-06-01_18:18 JST）

Trade[XYZ] 実データhardening向けに、次を実装済み。

```text
WebSocket capture:
  uv run sis collect-trade-xyz-ws

WebSocket quality manifest:
  uv run sis build-trade-xyz-ws-quality

REST parity manifest:
  uv run sis build-trade-xyz-rest-parity
```

生成されるmanifest:

```text
data/manifests/trade_xyz_ws_capture_manifest.json
data/manifests/trade_xyz_ws_quality_manifest.json
data/manifests/trade_xyz_rest_parity_manifest.json
```

保存境界:

```text
WS raw:
  data/raw/ws/trade_xyz/

既存raw quotes:
  data/raw/quotes/trade_xyz/

ルール:
  WS raw と既存 raw quotes を混ぜない
  recv_ts_ms を source/oracle timestampとして使わない
```

## 0.1 WS smoke後の追加実装と実測（2026-06-01_19:51 JST）

`plan/TRADE_XYZ_AFTER_WS_SMOKE_DATA_READY_PLAN_2026-06-01.md` の T1 から T4 まで進めた。

実装済み:

```text
application-level heartbeat:
  timeout時に WebSocket protocol ping ではなく { "method": "ping" } を送る
  heartbeat_sent_count は送信した application ping 数
  pong_count は受信した { "channel": "pong" } row 数

deadline stop:
  source側にも stop_time_monotonic を渡し、期限後に追加ping待ちで残らないようにした

trades list payload symbol resolution:
  trades.data[] の coin が単一なら canonical_symbol / coin / path partition に反映する
  mixed coin payload は単一symbolとして扱わない
```

近接テスト:

```bash
uv run pytest -q tests/test_trade_xyz_ws_recorder.py tests/test_trade_xyz_ws_envelope.py tests/test_trade_xyz_ws_quality.py
uv run ruff check src/sis/venues/trade_xyz/ws_recorder.py src/sis/venues/trade_xyz/ws_envelope.py tests/test_trade_xyz_ws_recorder.py tests/test_trade_xyz_ws_envelope.py
uv run ruff format --check src/sis/venues/trade_xyz/ws_recorder.py src/sis/venues/trade_xyz/ws_envelope.py tests/test_trade_xyz_ws_recorder.py tests/test_trade_xyz_ws_envelope.py
```

確認済み:

```text
pytest:
  14 passed

ruff check:
  pass

ruff format --check:
  pass
```

heartbeat 実測:

```text
output:
  .tmp/trade_xyz_ws_deadline_probe_20260601_1945/

symbols:
  EWJ

subscriptions:
  trades

duration:
  1 minute

capture:
  row_count: 13
  reconnect_count: 0
  error_count: 0
  heartbeat_sent_count: 11
  pong_count: 11
  subscription_response_count: 1

quality:
  status: pass
  row_count: 13
  pong_count: 11
  gap_count: 0
  malformed_payload_count: 0
  unknown_symbol_count: 0
```

3symbol 1分 smoke:

```text
output:
  .tmp/trade_xyz_ws_smoke_multi_symbol_20260601_1920/

symbols:
  SP500
  XYZ100
  NVDA

subscriptions:
  bbo
  trades
  activeAssetCtx

capture:
  row_count: 807
  reconnect_count: 0
  error_count: 0
  subscription_response_count: 9

quality:
  status: pass
  row_count: 807
  gap_count: 0
  source_ts_gap_count: 0
  malformed_payload_count: 0
  unknown_symbol_count: 0
  duplicate_payload_count: 39

REST parity:
  status: pass
  request_error_count: 0
  missing_ws_symbols: []
  missing_rest_symbols: []
  mismatched_symbols: []
  known_gap_count: 0

disk usage:
  836K
```

3symbol 15分 smoke:

```text
output:
  .tmp/trade_xyz_ws_smoke_15m_20260601_1950/

symbols:
  SP500
  XYZ100
  NVDA

subscriptions:
  bbo
  trades
  activeAssetCtx

capture:
  row_count: 10408
  bytes_written: 9812449
  connection_count: 1
  reconnect_count: 0
  error_count: 0
  heartbeat_sent_count: 0
  pong_count: 0
  subscription_response_count: 9

quality:
  status: pass
  row_count: 10408
  gap_count: 0
  source_ts_gap_count: 0
  malformed_payload_count: 0
  unknown_symbol_count: 0
  bbo_bid_ask_inversion_count: 0
  duplicate_payload_count: 837

REST parity:
  status: pass
  request_error_count: 0
  missing_ws_symbols: []
  missing_rest_symbols: []
  mismatched_symbols: []
  known_gap_count: 0

disk usage:
  9.5M
```

3symbol 60分 smoke:

```text
output:
  .tmp/trade_xyz_ws_smoke_60m_20260601_2015/

symbols:
  SP500
  XYZ100
  NVDA

subscriptions:
  bbo
  trades
  activeAssetCtx

capture:
  row_count: 47254
  bytes_written: 44412326
  connection_count: 1
  reconnect_count: 0
  error_count: 0
  heartbeat_sent_count: 0
  pong_count: 0
  subscription_response_count: 9

quality:
  status: pass
  row_count: 47254
  gap_count: 0
  source_ts_gap_count: 0
  malformed_payload_count: 0
  unknown_symbol_count: 0
  bbo_bid_ask_inversion_count: 0
  duplicate_payload_count: 3043
  subscription_counts:
    __control__: 9
    activeAssetCtx: 10524
    bbo: 32978
    trades: 3743
  symbol_counts:
    NVDA: 14194
    SP500: 12354
    XYZ100: 20697

REST parity:
  status: pass
  request_error_count: 0
  missing_ws_symbols: []
  missing_rest_symbols: []
  mismatched_symbols: []
  known_gap_count: 0

disk usage:
  43M
```

追加docs:

```text
runbook:
  docs/TRADE_XYZ_WS_COLLECTION_RUNBOOK_2026-06-01.md

WS raw field inventory:
  docs/集めるべき実データ0531-2108/README.md
```

途中で見つかった問題と対処:

```text
1. 初回の3symbol 1分 smokeでは trades.data[] が list のため symbol=__all__ になり、unknown_symbol_count=50 になった。
   対処: list内の coin が単一なら symbol 解決に使うよう修正した。

2. 初回の15分 smokeでは期限後の無通信で process が残った。
   対処: source側で deadline を見て、期限後は追加ping待ちに入らず終了するよう修正した。
```

まだ完了していないこと:

```text
3symbol 60分 smoke:
  完了。2026-06-01_20:54 JST 時点でpass。

11symbol 60分 smoke:
  未実行

24時間 read-only 観測:
  未実行

Current Real Data Contract更新:
  一部完了。WS raw field inventoryとbacktest入力昇格前条件は追記済み。
  backtest ingestion planへの正式引き継ぎは未完了。

runbook作成:
  完了。docs/TRADE_XYZ_WS_COLLECTION_RUNBOOK_2026-06-01.md を追加済み。

data-ready判定:
  未完了。まだ backtest_data_ready と呼んではいけない。
```

## 1. 目的

このRepoでは、Trade[XYZ] の純粋バックテストに流すための実データを集めている。

今回の目的は戦略最適化ではない。目的は、Trade[XYZ] の実データを誤読せず、`run_backtest()` へ流せる状態まで hardening することである。

スコープ外:

```text
live order
paper order
wallet
signing
exchange write
MT5
IC Markets
CFD
short
multi-symbol backtest
leverage
L2 replay
```

## 2. 現在の結論

現時点では、実務バックテスト用の全データ収集は完了していない。

最新の collection status:

```text
decision: COLLECT_MORE_QUOTES
backtest_data_ready: false
readiness_decision: NOT_READY
fail_count: 2
known_gap_count: 1
failing_requirements:
  - quote_coverage
  - real_market_reference
known_gap_requirements:
  - oracle_timestamp_provenance
```

account-specific fee は解決済みである。

```text
account_fee_manifest_status: pass
account_fee_manifest_user_matches_env: true
account_fee_user_taker_fee_bps: 4.5
account_fee_user_maker_fee_bps: 1.5
user_address_sha256:
  bc21e277c128ec8b528879da14eed5c0a7eba06e762cc79873cef63e77966e83
```

したがって、この状態を「実務BT ready」と呼んではいけない。ただし、feeだけを理由に止まっている状態ではない。

## 3. 根拠コマンド

現在状態は以下で再計算して確認した。

```bash
uv run sis build-trade-xyz-reference-data
SIS_TRADE_XYZ_ACCOUNT_FEE_USER_ADDRESS=<public-user-address> \
  uv run sis trade-xyz-collection-status --refresh-coverage --refresh-readiness
```

根拠artifact:

```text
data/ops/trade_xyz_collection_status.json
data/reports/trade_xyz_collection_status.md
data/manifests/trade_xyz_data_readiness_manifest.json
data/manifests/trade_xyz_quote_coverage_manifest.json
data/manifests/trade_xyz_account_fee_manifest.json
data/manifests/trade_xyz_real_market_reference_manifest.json
data/manifests/oracle_timestamp_manifest.json
data/archive/pre_2026_05_31_unusable_real_data/ARCHIVE_MANIFEST.json
```

確認時点:

```text
data/ops/trade_xyz_collection_status.json:
  generated_at: 2026-06-01T06:03:43.402583+00:00

data/manifests/trade_xyz_data_readiness_manifest.json:
  generated_at: 2026-06-01T06:03:43.402583+00:00
```

## 4. 重要な現在ルール

### 4.1 2026-05-30以前の実データは禁止

2026-05-30 以前の実データは、現在のTrade[XYZ] backtest/readiness作業では使えない。

該当データは archive 済みである。

```text
archive root:
  data/archive/pre_2026_05_31_unusable_real_data/

archive manifest:
  data/archive/pre_2026_05_31_unusable_real_data/ARCHIVE_MANIFEST.json

moved_count:
  75

policy:
  All real data dated 2026-05-30 or earlier is unusable for current Trade[XYZ] backtest/readiness work and must remain archived.
```

古い raw quotes、funding history、normalized parquet、research artifacts、paper artifacts、evidence artifacts、古いstatus/manifest/report がこのarchiveに入っている。

### 4.2 収集対象は設定ファイルから読む

非秘密の収集設定は、コードやshell scriptに直書きしない。

正本:

```text
configs/trade_xyz_data_collection.yaml
```

このYAMLが持つもの:

```text
symbols
quote_collection.duration_minutes
quote_collection.interval_seconds
readiness.min_days
readiness.max_gap_minutes
readiness.max_oracle_lag_minutes
signal_candles.intervals
signal_candles.period_days
historical_archive.coins
historical_archive.start_date
data_cutoff.usable_start_date
```

秘密情報や環境依存情報はYAMLに入れない。

YAMLに入れないもの:

```text
AWS credentials
AWS profile value
wallet secret
private key
account fee user address
API key
```

## 5. 現在の実行状態

collector と supervisor は動いている。

```text
collector_running: true
collector_process_count: 4
supervisor_running: true
supervisor_process_count: 2
progress_status: collecting_ok
latest_file_stale: false
cycle_lock_stale: false
supervisor_lock_stale: false
```

quote収集は止まっていない。理由なくcollectorを止める必要はない。

## 6. 現在使えるもの

| 項目 | 状態 | 備考 |
|---|---|---|
| Trade[XYZ] quote collector | 稼働中 | `collecting_ok` |
| signal candles | pass | `row_count=571`, `symbol_count=11`, `request_error_count=0` |
| funding events | pass | `source=quote_snapshot_hourly_bucket`, `row_count=187`, `skipped={}` |
| fee snapshots | pass | symbol-level fee snapshotsあり |
| account-specific fee | pass | userFees由来、taker `4.5bps`, maker `1.5bps` |
| session / reference dataset生成 | 実装済み | readiness artifactに接続済み |
| collection config | 実装済み | `configs/trade_xyz_data_collection.yaml` |
| archive manifest | 作成済み | 5/30以前の実データ75件をarchive |

## 7. 現在使えないもの

| 項目 | 状態 | 理由 |
|---|---|---|
| 実務BT全体 | NOT_READY | `backtest_data_ready=false` |
| quote coverage | fail | 30日相当に達していない |
| real market reference | fail | 2026-05-31以降の取得で多くの株式/ETF/index proxyが欠損 |
| oracle timestamp provenance | known gap | source payloadにoracle timestamp fieldが無い |
| historical archive backfill | blocked | AWS credentialsが無く preflight fail。downloadは未実行 |

## 8. 現在の不足詳細

### 8.1 quote coverage

```text
failing_requirement:
  quote_coverage

coverage_passed:
  false

row_count:
  10318

raw_row_count:
  10318

traceable_only:
  true

completion_ratio_by_span:
  0.021836354993441356

min_span_days:
  0.6550906498032407

min_days_required:
  30.0

max_gap_seconds:
  151.034367

estimated_max_collection_days_required:
  30
```

11銘柄すべてが `span_days_below_min` で不足している。行数は伸びているが、30日相当の連続coverageにはまだ遠い。

### 8.2 real market reference

2026-05-30以前のreference dataをarchiveしたため、`--start 2026-05-31 --end 2026-06-03` で再取得した。

しかし provider は株式/ETF/index proxyの多くを返さず、現在 `real_market_reference` は fail である。

```text
status:
  fail

provider:
  yfinance

interval:
  1d

row_count:
  2

returned_symbols:
  EURUSD=X, USDJPY=X

missing_mapped_symbols:
  AAPL, AMD, AMZN, EWJ, GOOGL, META, MSFT, NVDA, QQQ, SPY, TSLA

missing_requested_symbols:
  AAPL, AMD, AMZN, EWJ, GOOGL, META, MSFT, NVDA, QQQ, SPY, TSLA, UUP, ^VIX
```

古いreference dataをarchiveから戻してfailを消してはいけない。

### 8.3 account-specific fee

解決済みである。

```text
source:
  hyperliquid_info_userFees

manifest:
  data/manifests/trade_xyz_account_fee_manifest.json

raw_artifact:
  data/raw/fees/trade_xyz_account/2026-06-01_bc21e277c128.json

status:
  pass

matches_configured_user:
  true

user_taker_fee_bps:
  4.5

user_maker_fee_bps:
  1.5
```

これは public user address による read-only `userFees` 取得であり、wallet/signing/exchange write は不要である。

### 8.4 oracle timestamp provenance

```text
oracle_timestamp_provenance_status:
  known_gap

row_count:
  10318

oracle_ts_present_count:
  0

oracle_ts_missing_count:
  10318

oracle_ts_missing_rate:
  1.0

oracle_ts_missing_reasons:
  asset_ctx_missing_oracle_timestamp_field: 10318
```

Repoの方針:

```text
source_ts_ms、recv timestamp、client timestampを oracle_ts_ms として流用しない。
asset context payloadに既知のoracle timestamp fieldがある場合だけ oracle_ts_ms として認める。
```

今回、`oracle_ts_ms` とは別に snapshot freshness proxy を追加した。

```text
oracle_freshness_proxy:
  description: Not oracle_ts_ms. This proxy measures raw snapshot lag using source_ts_ms and recv_ts_ms for rows that include oracle_price.
  observed_count: 8536
  missing_count: 1782
  observed_rate: 0.8272921108742004
  status_counts:
    observed_snapshot_lag: 8536
    invalid_clock_order: 1782
  lag_ms_min: 0
  lag_ms_max: 781
```

これは `oracle_ts_ms` の代替ではない。oracle timestamp provenance は引き続き known gap である。

### 8.5 historical archive

```text
historical_archive_bulk_plan_exists: true
historical_archive_bulk_plan_estimated_total_object_count: 7950
historical_archive_bulk_execution_status: planned
historical_archive_bulk_execution_dry_run: true
historical_archive_bulk_execution_selected_object_count: 10
historical_archive_bulk_execution_downloaded_object_count: 0
historical_archive_bulk_execution_command_error_count: 0
```

preflightはAWS credentials不足で失敗している。

```text
preflight_return_code: 255
stderr: Unable to locate credentials. You can configure credentials by running "aws configure".
```

requester-pays download は未実行である。費用承認なしに `--execute --acknowledge-requester-pays` を実行してはいけない。

## 9. 正しい次の手順

### 9.1 まずstatus確認

```bash
SIS_TRADE_XYZ_ACCOUNT_FEE_USER_ADDRESS=<public-user-address> \
  uv run sis trade-xyz-collection-status --refresh-coverage --refresh-readiness
```

### 9.2 collector継続

collectorが止まっている場合だけ起動する。

```bash
scripts/collect_trade_xyz_data_until_ready.sh
```

外部前提なしでquote coverageだけ伸ばす場合:

```bash
SIS_TRADE_XYZ_REQUIRE_ARCHIVE_PREFLIGHT=0 \
SIS_TRADE_XYZ_REQUIRE_ACCOUNT_FEE=0 \
scripts/collect_trade_xyz_data_until_ready.sh
```

### 9.3 historical archiveを使う場合

まずAWS credentialsを設定し、preflightを通す。

```bash
uv run sis check-trade-xyz-historical-archive-preflight
uv run sis execute-trade-xyz-historical-archive-bulk --max-objects 10
```

dry-run確認後、費用と対象objectを承認してからだけ実行する。

```bash
uv run sis execute-trade-xyz-historical-archive-bulk \
  --execute \
  --acknowledge-requester-pays \
  --max-objects 10
```

### 9.4 real market referenceを再取得する場合

市場営業日を含む期間で再取得する。

```bash
uv run sis collect-trade-xyz-real-market-reference \
  --start 2026-05-31 \
  --end 2026-06-03 \
  --interval 1d
```

ただし、2026-05-30以前のreference dataを戻してはいけない。

### 9.5 完了判定

```bash
uv run sis trade-xyz-collection-status --strict --fail-on-not-ready
```

このコマンドが exit 0 になるまで、全データ収集は完了ではない。

## 10. やってはいけないこと

```text
2026-05-30以前の実データを戻してready判定に使う
archive配下のデータを現行data/へ手動コピーする
source_ts_ms / recv_ts_ms / client timestampをoracle_ts_msとして偽装する
oracle_freshness_proxyをoracle_ts_msの代替として扱う
signal candlesとfill snapshot quotesを同じbar入力に混ぜる
real market referenceの欠損を古いデータで埋める
collector/supervisorを理由なくkillする
requester-pays downloadを費用承認なしに実行する
live/paper/wallet/signing/exchange writeへ進む
```

## 11. 第三者向けまとめ

このRepoは、Trade[XYZ]実データ収集の仕組み自体は揃ってきている。collector、readiness、coverage、signal candles、funding、archive preflight、account fee collection、status reportは実装済みである。

しかし、現在はまだ `NOT_READY` である。主な理由は、30日quote coverage不足、2026-05-31以降だけに制限したreal market referenceの欠損、oracle timestamp provenanceのsource欠損である。

次の担当者は、まず `configs/trade_xyz_data_collection.yaml` と `trade-xyz-collection-status` を見る。5/30以前のデータは使わず、AWS/requester-paysやreal-market referenceの外部前提を埋めてから、strict readiness gateを通す。
