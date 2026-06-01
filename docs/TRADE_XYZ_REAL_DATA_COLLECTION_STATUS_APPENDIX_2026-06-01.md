# Trade[XYZ] Real Data Collection Status Appendix

作成日: 2026-06-01 JST

この付録は、Trade[XYZ] の純粋バックテストに必要な実データ収集の現在地を、現在のRepoと生成済みmanifestを正として整理する。戦略最適化やlive/paper/wallet/signing/exchange writeの計画ではない。

## 2026-05-30以前の実データ禁止

2026-05-30 以前の実データは、現在のTrade[XYZ]バックテスト/readiness作業では使わない。該当データは次の場所へarchiveした。

```text
data/archive/pre_2026_05_31_unusable_real_data/
data/archive/pre_2026_05_31_unusable_real_data/ARCHIVE_MANIFEST.json
```

archive対象には、2026-05-27/2026-05-28 の raw Trade[XYZ] quotes、5/30以前を含む normalized parquet、funding history、real market reference、research/paper/evidence artifacts、古いstatus/manifest/reportを含めた。

現在の `data/normalized/quotes.parquet` は、残っている raw quotes から再生成済みで、確認時点の範囲は以下である。

```text
min ts_client: 2026-05-31T14:02:09.517202Z
max ts_client: 2026-05-31T21:43:00.205458Z
rows: 4851
```

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
  period_days: 1
historical_archive:
  start_date: 2026-05-31
```

実行環境ごとの差分は、CLI引数または `SIS_TRADE_XYZ_*` 環境変数で上書きする。秘密情報、AWS profile、account fee用public user addressは、このYAMLへ入れない。

## 結論

現時点では、実務バックテスト用の全データ収集は完了していない。

最新statusでは以下の判定になっている。

```text
decision: COLLECT_MORE_QUOTES
backtest_data_ready: false
readiness_decision: NOT_READY
fail_count: 1
known_gap_count: 3
failing_requirements: quote_coverage
known_gap_requirements:
  - account_specific_fee
  - funding_events
  - oracle_timestamp_provenance
```

collector と supervisor は稼働中で、quote coverage は伸びている。ただし、30日coverage、account-specific fee、funding history join、oracle timestamp provenance が未充足である。

## 根拠

この文書は以下のコマンドとartifactを根拠にする。

```bash
uv run sis trade-xyz-collection-status --no-refresh-coverage --no-refresh-readiness
scripts/check_trade_xyz_data_prereqs.sh
```

主要artifact:

```text
data/ops/trade_xyz_collection_status.json
data/reports/trade_xyz_collection_status.md
data/manifests/trade_xyz_data_readiness_manifest.json
data/manifests/trade_xyz_quote_coverage_manifest.json
data/manifests/funding_history_join_manifest.json
data/manifests/trade_xyz_historical_archive_preflight_manifest.json
data/manifests/trade_xyz_signal_candles_manifest.json
data/manifests/trade_xyz_real_market_reference_manifest.json
```

確認時点のstatus artifact:

```text
data/ops/trade_xyz_collection_status.json generated_at:
  2026-05-31T21:36:31.171195+00:00

data/manifests/trade_xyz_data_readiness_manifest.json generated_at:
  2026-05-31T21:30:28.976057+00:00
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
| signal candles | pass | `row_count=67147`, `symbol_count=11`, `request_error_count=0` | signal inputとして利用可 |
| real market reference | pass | `provider=yfinance`, `interval=1d`, `row_count=3768` | regime/reference用に利用可 |
| reference datasets | pass | registry/fee/session/funding base artifactsあり | 参照datasetは生成済み |
| session state | pass | `row_count=3335`, `closed=2365`, `regular=970` | session filterの根拠として利用可 |
| fee snapshots | pass | symbol-level fee snapshotあり | symbol-level feeには利用可 |

## まだ使えないもの

| 項目 | 状態 | 具体値 / 根拠 | 必要な対応 |
|---|---|---:|---|
| quote coverage | fail | `coverage_passed=false`, `row_count=4708`, `coverage_completion_ratio_by_span=0.009948866551311728` | 30日相当まで収集継続、またはarchive backfill |
| account-specific fee | known gap | `account_fee_user_address_configured=false`, `account_fee_manifest_exists=false` | `SIS_TRADE_XYZ_ACCOUNT_FEE_USER_ADDRESS` を設定して収集 |
| funding history join | known gap | `funding_events_from_history.row_count=109`, `missing_oracle_quote_within_lag=1112` | quote/oracle coverage増加後にbundle再生成 |
| oracle timestamp provenance | known gap | `oracle_ts_present_count=0`, `oracle_ts_missing_count=3335`, `oracle_ts_missing_rate=1.0` | source payloadに無いtimestampは偽装しない |
| historical archive backfill | blocked | `status=fail`, `return_code=255`, `Unable to locate credentials` | AWS credentials または `SIS_AWS_COMMAND` 設定 |

## Quote Coverageの現状

coverage manifestの要点:

```text
coverage_passed: false
symbol_count: 11
row_count: 4708
raw_row_count: 5678
traceable_only: true
excluded_missing_raw_payload_ref_count: 970
raw_payload_ref_missing_rate_all_rows: 0.17083480098626277
min_days_required: 30.0
```

11銘柄はいずれも `span_days_below_min` で不足している。代表値として、各symbolの現在の有効spanは約 `0.298466 days` であり、必要な30日には届いていない。

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

## Fundingの現状

funding history joinは生成済みだが、完全ではない。

```text
data/manifests/funding_history_join_manifest.json:
  row_count: 109
  usable_as_backtest_funding_event: true
  max_oracle_lag_minutes: 90.0
  skipped:
    missing_oracle_quote_within_lag: 1112
```

このため、funding込み評価は条件付きでしか使えない。`funding_events_from_history.parquet` を使う場合は、必ず `funding_history_join_manifest.json` の `skipped` と oracle join lag provenance を確認する。

## Oracle Timestampの現状

oracle timestamp provenanceは known gap である。

```text
oracle_ts_present_count: 0
oracle_ts_missing_count: 3335
oracle_ts_missing_rate: 1.0
oracle_ts_missing_reasons:
  missing_reason_not_recorded: 970
  asset_ctx_missing_oracle_timestamp_field: 2365
```

Repoの方針:

```text
source_ts_ms、recv timestamp、client timestampを oracle_ts_ms として流用しない。
asset context payloadに既知のoracle timestamp fieldがある場合だけ oracle_ts_ms として認める。
```

これは「実装漏れ」ではなく、誤読防止のための制約である。

## Account Feeの現状

account-specific feeは未収集である。

```text
account_fee_user_address_configured: false
account_fee_manifest_exists: false
account_fee_manifest_status: null
account_fee_user_taker_fee_bps: null
account_fee_user_maker_fee_bps: null
```

収集には public user address が必要である。

```bash
export SIS_TRADE_XYZ_ACCOUNT_FEE_USER_ADDRESS=0x...
uv run sis collect-trade-xyz-account-fee --user-address "$SIS_TRADE_XYZ_ACCOUNT_FEE_USER_ADDRESS"
uv run sis build-trade-xyz-data-readiness
```

秘密鍵、wallet、signing、exchange writeは不要であり、使わない。

## Historical Archiveの現状

archive bulk planはあるが、downloadは進んでいない。

```text
historical_archive_bulk_plan_exists: true
historical_archive_bulk_plan_estimated_total_object_count: 7950
historical_archive_bulk_execution_status: blocked_preflight_failed
historical_archive_bulk_execution_selected_object_count: 1
historical_archive_bulk_execution_downloaded_object_count: 0
historical_archive_bulk_execution_command_error_count: 0
```

preflightはAWS credentials不足で失敗している。

```text
status: fail
return_code: 255
stderr: Unable to locate credentials. You can configure credentials by running "aws configure".
```

必要な設定:

```bash
export SIS_AWS_COMMAND="aws --profile <profile>"
uv run sis check-trade-xyz-historical-archive-preflight
```

requester-pays downloadを実行する前に、費用、対象object数、対象coin名を確認すること。

## 現在の正しい次手

### 1. Collectorを止めない

collectorは現在動いている。外部前提が未設定でも、quote coverageだけは伸ばせる。

確認:

```bash
uv run sis trade-xyz-collection-status --no-refresh-coverage --no-refresh-readiness
```

collectorが止まっている場合:

```bash
scripts/collect_trade_xyz_data_until_ready.sh
```

外部前提なしでquote collectionだけ継続する場合:

```bash
SIS_TRADE_XYZ_REQUIRE_ARCHIVE_PREFLIGHT=0 \
SIS_TRADE_XYZ_REQUIRE_ACCOUNT_FEE=0 \
scripts/collect_trade_xyz_data_until_ready.sh
```

### 2. 外部前提を埋める

```bash
scripts/check_trade_xyz_data_prereqs.sh
```

現在は以下で止まる。

```text
AWS credentials: missing
SIS_TRADE_XYZ_ACCOUNT_FEE_USER_ADDRESS: missing
```

### 3. 最新rawをbundle/readinessへ反映する

```bash
uv run sis build-trade-xyz-data-bundle --auto-funding-window
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
oracle_timestamp_provenance: pass または仕様上許容する明示的な例外
signal_candles: pass
real_market_reference: pass
session_state: pass
```

例外を許す場合でも、`READY_WITH_KNOWN_GAPS` を「完全な実務ready」と呼んではいけない。何をknown gapとして許したかをreportとmanifestに残す。

## 実務上の判定

現在できること:

```text
collectorの継続運用
signal candlesを使ったsignal側の検証
real market referenceを使ったregime/reference検証
小規模なplumbing smoke
readiness / coverage / prereq監視
```

現在やってはいけないこと:

```text
この状態を実務バックテストreadyと呼ぶ
30日coverage不足を無視する
account feeをsymbol-level fallbackだけで実アカウントfeeとして扱う
oracle_ts_msをrecv/client/source timestampで埋める
funding join skippedを無視してfunding込み成績を断定する
signal candlesとfill snapshot quotesをbar集約で混ぜる
```

## 参照先

```text
docs/OPERATIONS_RUNBOOK.md
docs/集めるべき実データ0531-2108/README.md
data/reports/trade_xyz_collection_status.md
data/ops/trade_xyz_collection_status.json
.ai_memory/HANDOFF.md
```
