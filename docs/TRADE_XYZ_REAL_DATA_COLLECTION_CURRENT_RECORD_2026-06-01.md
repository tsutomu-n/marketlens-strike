# Trade[XYZ] Real Data Collection Current Record

作成日: 2026-06-01 JST

この文書は、第三者が `marketlens-strike` の現在状態を引き継ぐための記録である。コード、設定、生成済みstatus artifactを正として書く。

## 1. 目的

このRepoでは、Trade[XYZ] の純粋バックテストに流すための実データを集めている。

今回の作業目的は、戦略最適化ではない。目的は、Trade[XYZ] の実データを誤読せず、`run_backtest()` へ流せる状態まで hardening することである。

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

最新の collection status は以下である。

```text
decision: COLLECT_MORE_QUOTES
backtest_data_ready: false
readiness_decision: NOT_READY
fail_count: 2
known_gap_count: 2
failing_requirements:
  - quote_coverage
  - real_market_reference
known_gap_requirements:
  - account_specific_fee
  - oracle_timestamp_provenance
```

したがって、この状態を「実務BT ready」と呼んではいけない。

## 3. 根拠コマンド

現在状態は以下で確認した。

```bash
uv run sis trade-xyz-collection-status --no-refresh-coverage --no-refresh-readiness
```

注意:

```text
このコマンドは status report を更新するが、coverage/readiness manifestを再計算しない。
最終判定では --refresh-coverage --refresh-readiness、または --strict --fail-on-not-ready を使う。
この文書の数値は確認時点のsnapshotであり、作業前にstatusを再取得する。
```

根拠artifact:

```text
data/ops/trade_xyz_collection_status.json
data/reports/trade_xyz_collection_status.md
data/manifests/trade_xyz_data_readiness_manifest.json
data/archive/pre_2026_05_31_unusable_real_data/ARCHIVE_MANIFEST.json
```

確認時点:

```text
data/ops/trade_xyz_collection_status.json:
  generated_at: 2026-06-01T05:22:13.015984+00:00

data/manifests/trade_xyz_data_readiness_manifest.json:
  generated_at: 2026-05-31T21:49:15.715134+00:00
  note: status artifactより古い。--no-refresh-readinessで確認したため。
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

これらは環境変数またはCLI引数で渡す。

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

つまり、quote収集は止まっていない。今すぐやるべきことは collector を殺すことではなく、収集を継続しつつ不足項目を埋めることである。

## 6. 現在使えるもの

| 項目 | 状態 | 備考 |
|---|---|---|
| Trade[XYZ] quote collector | 稼働中 | `collecting_ok` |
| signal candles | pass | `row_count=571`, `symbol_count=11`, `request_error_count=0` |
| funding events | pass | `source=quote_snapshot_hourly_bucket`, `row_count=88`, `skipped={}` |
| session / reference dataset生成 | 実装済み | readiness artifactに接続済み |
| collection config | 実装済み | `configs/trade_xyz_data_collection.yaml` |
| archive manifest | 作成済み | 5/30以前の実データ75件をarchive |

## 7. 現在使えないもの

| 項目 | 状態 | 理由 |
|---|---|---|
| 実務BT全体 | NOT_READY | `backtest_data_ready=false` |
| quote coverage | fail | 30日相当に達していない |
| real market reference | fail | 2026-05-31が市場休場で、多くの株式/ETF/index proxyが欠損 |
| account-specific fee | known gap | `SIS_TRADE_XYZ_ACCOUNT_FEE_USER_ADDRESS` 未設定 |
| oracle timestamp provenance | known gap | source payloadにoracle timestamp fieldが無い |
| historical archive backfill | blocked | AWS credentialsが無く preflight fail |

## 8. 現在の不足詳細

### 8.1 quote coverage

```text
failing_requirement:
  quote_coverage

coverage_completion_ratio_by_span:
  0.010391765288194443

coverage_passed:
  false

row_count:
  4917

raw_row_count:
  4917

traceable_only:
  true

estimated_max_collection_days_required:
  30
```

30日相当の連続coverageにはまだ遠い。collectorを継続するか、AWS credentialsを設定して historical archive backfill を使う必要がある。

### 8.2 real market reference

2026-05-30以前のreference dataをarchiveしたため、`--start 2026-05-31` で再取得した。

しかし 2026-05-31 は市場休場に当たり、SPY / QQQ / NVDA / AAPL / MSFT などが欠損した。そのため現在 `real_market_reference` は fail である。

このfailは、古いデータを使わないルールを守った結果であり、無理に5/30以前のreferenceを戻して解消してはいけない。

現在のmanifest値:

```text
status:
  fail

row_count:
  2

returned_symbols:
  EURUSD=X, USDJPY=X

missing_mapped_symbols:
  AAPL, AMD, AMZN, EWJ, GOOGL, META, MSFT, NVDA, QQQ, SPY, TSLA

missing_requested_symbols:
  AAPL, AMD, AMZN, EWJ, GOOGL, META, MSFT, NVDA, QQQ, SPY, TSLA, UUP, ^VIX
```

### 8.3 account-specific fee

```text
account_fee_user_address_configured: false
account_fee_manifest_exists: false
```

必要なもの:

```bash
export SIS_TRADE_XYZ_ACCOUNT_FEE_USER_ADDRESS=0x...
uv run sis collect-trade-xyz-account-fee --user-address "$SIS_TRADE_XYZ_ACCOUNT_FEE_USER_ADDRESS"
uv run sis build-trade-xyz-data-readiness
```

この取得は public user address による read-only `userFees` 取得であり、wallet/signing/exchange write は不要。

### 8.4 oracle timestamp provenance

```text
oracle_timestamp_provenance_status: known_gap
oracle_ts_missing_rate: 1.0
```

Repoの方針:

```text
source_ts_ms、recv timestamp、client timestampを oracle_ts_ms として流用しない。
asset context payloadに既知のoracle timestamp fieldがある場合だけ oracle_ts_ms として認める。
```

これは誤読防止のための制約である。

### 8.5 historical archive

```text
historical_archive_bulk_plan_exists: true
historical_archive_bulk_plan_estimated_total_object_count: 7950
historical_archive_bulk_execution_status: blocked_preflight_failed
next archive plan:
  start-date: 2026-05-31
  end-date: 2026-05-31
```

preflightはAWS credentials不足で失敗している。

```text
preflight_return_code: 255
stderr: Unable to locate credentials. You can configure credentials by running "aws configure".
```

## 9. 正しい次の手順

### 9.1 まずstatus確認

```bash
uv run sis trade-xyz-collection-status --no-refresh-coverage --no-refresh-readiness
```

### 9.2 外部前提の確認

```bash
scripts/check_trade_xyz_data_prereqs.sh
```

現在はAWS credentialsとaccount fee user addressで止まる。

### 9.3 collector継続

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

### 9.4 設定を変更する場合

対象symbolやintervalを変更する場合は、まずここを編集する。

```text
configs/trade_xyz_data_collection.yaml
```

dry-run確認:

```bash
uv run sis collect-trade-xyz-data-cycle --dry-run --use-existing-registry
```

### 9.5 bundle/readiness再生成

```bash
uv run sis build-trade-xyz-data-bundle --auto-funding-window
uv run sis trade-xyz-collection-status --refresh-coverage --refresh-readiness
```

`data/manifests/trade_xyz_data_readiness_manifest.json` だけを見て最新状態だと判断してはいけない。`--no-refresh-readiness` を使った直後は、status artifactだけが新しく、readiness manifestは古いままの場合がある。

### 9.6 完了判定

```bash
uv run sis trade-xyz-collection-status --strict --fail-on-not-ready
```

このコマンドが exit 0 になるまで、全データ収集は完了ではない。

## 10. やってはいけないこと

```text
2026-05-30以前の実データを戻してready判定に使う
archive配下のデータを現行data/へ手動コピーする
archive済みデータを手動で戻して不足を解消したことにする
古いreadiness manifestを最新statusと同一視する
source_ts_ms / recv_ts_ms / client timestampをoracle_ts_msとして偽装する
signal candlesとfill snapshot quotesを同じbar入力に混ぜる
account feeを未取得のまま実アカウントfeeとして扱う
real market referenceの休場欠損を古いデータで埋める
collector/supervisorを理由なくkillする
live/paper/wallet/signing/exchange writeへ進む
```

## 11. 関連ドキュメント

```text
docs/TRADE_XYZ_REAL_DATA_COLLECTION_STATUS_APPENDIX_2026-06-01.md
docs/TRADE_XYZ_DOCS_CODE_TRUTH_AUDIT_2026-06-01.md
docs/OPERATIONS_RUNBOOK.md
docs/集めるべき実データ0531-2108/README.md
docs/CODE_STATUS.md
.ai_memory/HANDOFF.md
```

## 12. 第三者向けまとめ

このRepoは、Trade[XYZ]実データ収集の仕組み自体はかなり揃っている。collector、readiness、coverage、signal candles、funding、archive preflight、account fee collection、status reportは実装済みである。

しかし、現在はまだ `NOT_READY` である。主な理由は、30日quote coverage不足、2026-05-31以降だけに制限したreal market referenceの休場欠損、account fee user address未設定、oracle timestamp provenanceのsource欠損である。

次の担当者は、まず `configs/trade_xyz_data_collection.yaml` と `trade-xyz-collection-status` を見ればよい。5/30以前のデータは使わず、AWS/account feeの外部前提を埋めてから、strict readiness gateを通す。
