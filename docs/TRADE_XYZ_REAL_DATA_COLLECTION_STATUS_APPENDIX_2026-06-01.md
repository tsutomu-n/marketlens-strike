# Trade[XYZ] Real Data Collection Status Appendix

更新日: 2026-06-01_15:03 JST

この付録は、Trade[XYZ] の純粋バックテストに必要な実データ収集の現在地を、現在のRepoと生成済みmanifestを正として整理する。戦略最適化や live/paper/wallet/signing/exchange write の計画ではない。

## 2026-05-30以前の実データ禁止

2026-05-30 以前の実データは、現在のTrade[XYZ]バックテスト/readiness作業では使わない。該当データは次の場所へarchiveした。

```text
data/archive/pre_2026_05_31_unusable_real_data/
data/archive/pre_2026_05_31_unusable_real_data/ARCHIVE_MANIFEST.json
```

archive対象には、2026-05-27/2026-05-28 の raw Trade[XYZ] quotes、5/30以前を含む normalized parquet、funding history、real market reference、research/paper/evidence artifacts、古いstatus/manifest/reportを含めた。

この日付制約により、5/30以前を含む signal candles、real market reference、research artifacts は再取得または再生成するまで使ってはいけない。

## 収集対象設定の正本

非秘密の収集対象symbol、quote収集間隔、signal candle interval、readiness閾値は、コードやshell scriptへ直書きせず、次の設定ファイルから読む。

```text
configs/trade_xyz_data_collection.yaml
```

現在の設定:

```text
symbols:
  AAPL, AMD, AMZN, EWJ, GOOGL, META, MSFT, NVDA, SP500, TSLA, XYZ100
quote_collection:
  duration_minutes: 1440
  interval_seconds: 60
signal_candles:
  intervals: 30m, 4h, 1d, 3d
historical_archive:
  start_date: 2026-05-31
```

秘密情報、AWS profile、account fee用public user addressは、このYAMLへ入れない。

## 結論

現時点では、実務バックテスト用の全データ収集は完了していない。

最新status:

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

collector と supervisor は稼働中で、quote coverage は伸びている。ただし、30日coverage、real market reference、oracle timestamp provenance が未充足である。

account-specific fee は解決済みで、known gapではない。

## 根拠

この文書は以下のコマンドとartifactを根拠にする。

```bash
uv run sis build-trade-xyz-reference-data
SIS_TRADE_XYZ_ACCOUNT_FEE_USER_ADDRESS=<public-user-address> \
  uv run sis trade-xyz-collection-status --refresh-coverage --refresh-readiness
```

主要artifact:

```text
data/ops/trade_xyz_collection_status.json
data/reports/trade_xyz_collection_status.md
data/manifests/trade_xyz_data_readiness_manifest.json
data/manifests/trade_xyz_quote_coverage_manifest.json
data/manifests/funding_manifest.json
data/manifests/oracle_timestamp_manifest.json
data/manifests/trade_xyz_account_fee_manifest.json
data/manifests/trade_xyz_historical_archive_preflight_manifest.json
data/manifests/trade_xyz_signal_candles_manifest.json
data/manifests/trade_xyz_real_market_reference_manifest.json
```

確認時点のartifact:

```text
data/ops/trade_xyz_collection_status.json generated_at:
  2026-06-01T06:03:43.402583+00:00

data/manifests/trade_xyz_data_readiness_manifest.json generated_at:
  2026-06-01T06:03:43.402583+00:00
```

## 現在使えるもの

| 項目 | 状態 | 具体値 / 根拠 | 実務上の扱い |
|---|---|---:|---|
| quote collector | 稼働中 | `collector_running=true`, `collector_process_count=4` | 継続収集中 |
| until-ready supervisor | 稼働中 | `supervisor_running=true`, `supervisor_process_count=2` | 監視継続中 |
| progress | 正常 | `progress_status=collecting_ok` | collector停止ではない |
| latest raw quote | staleではない | `latest_file_stale=false` | 収集は止まっていない |
| cycle lock | staleではない | `cycle_lock_stale=false` | 重複・死活異常なし |
| supervisor lock | staleではない | `supervisor_lock_stale=false` | 監視lock異常なし |
| signal candles | pass | `row_count=571`, `symbol_count=11`, `request_error_count=0` | signal inputとして利用可 |
| funding events | pass | `source=quote_snapshot_hourly_bucket`, `row_count=187`, `skipped={}` | funding event seriesとして利用可 |
| reference datasets | pass | registry/fee/session/funding base artifactsあり | 参照datasetは生成済み |
| fee snapshots | pass | `fee_snapshot_count=11` | symbol-level feeに利用可 |
| account-specific fee | pass | taker `4.5bps`, maker `1.5bps` | 実アカウントfeeとして利用可 |

## まだ使えないもの

| 項目 | 状態 | 具体値 / 根拠 | 必要な対応 |
|---|---|---:|---|
| quote coverage | fail | `coverage_passed=false`, `row_count=10318`, `completion_ratio_by_span=0.021836354993441356` | 30日相当まで収集継続、またはarchive backfill |
| real market reference | fail | `row_count=2`, returned only `EURUSD=X`, `USDJPY=X` | 開場日を含む期間または別providerで再取得 |
| oracle timestamp provenance | known gap | `oracle_ts_present_count=0`, `oracle_ts_missing_count=10318`, `oracle_ts_missing_rate=1.0` | source payloadに無いtimestampは偽装しない |
| historical archive backfill | blocked | preflight `return_code=255`, AWS credentials missing | AWS credentials または `SIS_AWS_COMMAND` 設定。費用承認後のみexecute |

## Quote Coverageの現状

coverage manifestの要点:

```text
coverage_passed: false
symbol_count: 11
row_count: 10318
raw_row_count: 10318
traceable_only: true
excluded_missing_raw_payload_ref_count: 0
raw_payload_ref_missing_rate_all_rows: 0.0
min_span_days: 0.6550906498032407
max_span_days: 0.6550906498032407
completion_ratio_by_span: 0.021836354993441356
max_gap_seconds: 151.034367
min_days_required: 30.0
```

11銘柄はいずれも `span_days_below_min` で不足している。

対象symbol:

```text
AAPL
AMD
AMZN
EWJ
GOOGL
META
MSFT
NVDA
SP500
TSLA
XYZ100
```

重要な読み方:

```text
traceable_only=true のcoverageで見る。
旧raw由来の raw_payload_ref 欠損行は、READY判定の母集団に混ぜない。
coverage_passed=false の間は、run_backtest()へ実務投入できる状態ではない。
```

## Signal FieldsとFill Snapshot Fieldsの分離

現在のRepoでは、signal用のhistorical OHLCVとfill snapshot用のquote logsは別artifactで扱う。

```text
signal input:
  data/normalized/trade_xyz_signal_candles.parquet

fill snapshot / execution approximation:
  data/normalized/quotes.parquet
  data/raw/quotes/trade_xyz/*.jsonl
```

bar集約時に、signal fields と fill snapshot fields を混ぜてはいけない。`trade_xyz_signal_candles.parquet` は signal input、`quotes.parquet` は fill/cost/provenance 側の根拠である。

## Real Market Referenceの現状

real market reference は現在 fail である。5/30以前のreference dataをarchiveした後、`--start 2026-05-31 --end 2026-06-03` で再取得したが、株式/ETF/index proxyの多くが返らなかった。

```text
data/manifests/trade_xyz_real_market_reference_manifest.json:
  status: fail
  provider: yfinance
  interval: 1d
  row_count: 2
  returned_symbols:
    EURUSD=X, USDJPY=X
  missing_mapped_symbols:
    AAPL, AMD, AMZN, EWJ, GOOGL, META, MSFT, NVDA, QQQ, SPY, TSLA
  missing_requested_symbols:
    AAPL, AMD, AMZN, EWJ, GOOGL, META, MSFT, NVDA, QQQ, SPY, TSLA, UUP, ^VIX
```

古いreference dataをarchiveから戻してfailを消してはいけない。

## Fundingの現状

現行readinessが使っている funding events は quote snapshot 由来の hourly bucket series であり、passである。

```text
data/manifests/funding_manifest.json:
  source: quote_snapshot_hourly_bucket
  row_count: 187
  skipped:
    {}
```

## Oracle Timestampの現状

oracle timestamp provenanceは known gap である。

```text
oracle_ts_present_count: 0
oracle_ts_missing_count: 10318
oracle_ts_missing_rate: 1.0
oracle_ts_missing_reasons:
  asset_ctx_missing_oracle_timestamp_field: 10318
```

Repoの方針:

```text
source_ts_ms、recv timestamp、client timestampを oracle_ts_ms として流用しない。
asset context payloadに既知のoracle timestamp fieldがある場合だけ oracle_ts_ms として認める。
```

追加済みの proxy:

```text
oracle_freshness_proxy:
  observed_count: 8536
  missing_count: 1782
  observed_rate: 0.8272921108742004
  status_counts:
    observed_snapshot_lag: 8536
    invalid_clock_order: 1782
  lag_ms_min: 0
  lag_ms_max: 781
```

これは `oracle_ts_ms` ではない。oracle timestampが無い問題を解決したことにはならない。

## Account Feeの現状

account-specific feeは pass である。

```text
data/manifests/trade_xyz_account_fee_manifest.json:
  status: pass
  source: hyperliquid_info_userFees
  raw_artifact_path: data/raw/fees/trade_xyz_account/2026-06-01_bc21e277c128.json
  user_address_sha256: bc21e277c128ec8b528879da14eed5c0a7eba06e762cc79873cef63e77966e83
  configured_user_address_sha256: bc21e277c128ec8b528879da14eed5c0a7eba06e762cc79873cef63e77966e83
  matches_configured_user: true
  user_taker_fee_bps: 4.5
  user_maker_fee_bps: 1.5
  missing_fields: []
```

秘密鍵、wallet、signing、exchange writeは不要であり、使っていない。

## Historical Archiveの現状

archive bulk planはあるが、downloadは進んでいない。

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
status: fail
return_code: 255
stderr: Unable to locate credentials. You can configure credentials by running "aws configure".
```

requester-pays downloadを実行する前に、費用、対象object数、対象coin名を確認すること。

## 現在の正しい次手

### 1. Collectorを止めない

collectorは現在動いている。外部前提が未設定でも、quote coverageだけは伸ばせる。

確認:

```bash
SIS_TRADE_XYZ_ACCOUNT_FEE_USER_ADDRESS=<public-user-address> \
  uv run sis trade-xyz-collection-status --refresh-coverage --refresh-readiness
```

collectorが止まっている場合:

```bash
scripts/collect_trade_xyz_data_until_ready.sh
```

### 2. Historical archiveの外部前提を埋める

```bash
uv run sis check-trade-xyz-historical-archive-preflight
```

現在はAWS credentials不足で止まる。requester-pays downloadは費用承認後だけ実行する。

### 3. 最新rawをbundle/readinessへ反映する

```bash
uv run sis build-trade-xyz-reference-data
uv run sis build-trade-xyz-data-bundle --auto-funding-window
SIS_TRADE_XYZ_ACCOUNT_FEE_USER_ADDRESS=<public-user-address> \
  uv run sis trade-xyz-collection-status --refresh-coverage --refresh-readiness
```

### 4. 完了判定を行う

```bash
uv run sis trade-xyz-collection-status --strict --fail-on-not-ready
```

このコマンドが exit 0 になるまで、実務的に必要な全データ収集は完了ではない。

## 完了条件

最低限、以下をすべて満たす必要がある。

```text
backtest_data_ready: true
readiness_decision: READY
fail_count: 0
known_gap_count: 0
quote_coverage: pass
account_specific_fee: pass
funding_events: pass
signal_candles: pass
real_market_reference: pass
session_state: pass
oracle_timestamp_provenance: pass または仕様上許容する明示的な例外
```

例外を許す場合でも、`READY_WITH_KNOWN_GAPS` を「完全な実務ready」と呼んではいけない。何をknown gapとして許したかをreportとmanifestに残す。

## 実務上の判定

現在できること:

```text
collectorの継続運用
signal candlesを使ったsignal側の検証
account-specific fee込みのcost前提確認
小規模なplumbing smoke
readiness / coverage / prereq監視
```

現在やってはいけないこと:

```text
この状態を実務バックテストreadyと呼ぶ
30日coverage不足を無視する
real market referenceの欠損を古いarchive dataで埋める
oracle_freshness_proxyをoracle_ts_msの代替として扱う
古いreadiness manifestを最新statusと同一視する
signal candlesとfill snapshot quotesをbar集約で混ぜる
requester-pays downloadを費用承認なしに実行する
```

## 参照先

```text
docs/TRADE_XYZ_REAL_DATA_COLLECTION_CURRENT_RECORD_2026-06-01.md
docs/TRADE_XYZ_READINESS_GAP_INVESTIGATION_GUIDE_2026-06-01.md
docs/OPERATIONS_RUNBOOK.md
docs/集めるべき実データ0531-2108/README.md
data/reports/trade_xyz_collection_status.md
data/ops/trade_xyz_collection_status.json
.ai_memory/HANDOFF.md
```
