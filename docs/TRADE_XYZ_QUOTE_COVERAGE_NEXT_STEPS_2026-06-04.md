<!--
作成日: 2026-06-04_17:47 JST
更新日: 2026-06-04_17:47 JST
-->

# Trade[XYZ] Quote Coverage Next Steps 2026-06-04

この文書は、2026-06-04_16:39 JST に起動した24時間 read-only quote coverage cycle の次にやることを忘れないための運用メモである。

## 結論

いまは待つ。起動中の collector を止めない。

```text
現在の作業:
  24時間 read-only quote coverage cycle の完走待ち

起動時刻:
  2026-06-04_16:39 JST

予定完了:
  2026-06-05_16:39 JST 前後

起動中PID:
  2484910

log:
  logs/trade_xyz_data_cycle/trade_xyz_data_cycle_20260604_073932.log

raw quote file:
  data/raw/quotes/trade_xyz/2026-06-04.jsonl

2026-06-04_17:42 JST 時点:
  collector process alive
  raw quote rows: 693
  latest raw quote file updating
```

この1 cycle が完了しても、通常はまだ `backtest_data_ready=true` にはならない。30日 quote coverage 要件に対して、1日分ずつ積む段階である。

## 現在の前提

完了済み:

```text
WS acquisition / ingestion:
  24h WS raw run accepted
  WS raw -> QuoteLog adapter implemented
  WS raw -> parquet/DuckDB manifest implemented
  BBO bar + activeAssetCtx no-lookahead asof join implemented
  run_backtest smoke implemented

signal candles:
  request_error_count=0 に復旧済み
  429/partial failure hardening 実装済み
  failed key retry: 1回
  final failure: 既存成功raw/parquetを保持し error artifactへ分離

verification:
  ./scripts/check pass
  pytest 807 passed
```

未完了:

```text
backtest_data_ready:
  false

主な残り:
  quote_coverage 30日要件
  oracle_timestamp_provenance known gap

禁止:
  source_ts_ms / recv_ts_ms を oracle_ts_ms として埋めない
  2026-05-30以前の実データをready判定へ戻さない
  live / wallet / signing / exchange write へ進まない
```

## 1. 完了までの監視

通常は `2026-06-05_16:39 JST` 付近まで待つ。

途中で確認するなら、次の read-only commands だけ使う。

```bash
ps -fp 2484910
pgrep -aP 2484910 || true
tail -80 logs/trade_xyz_data_cycle/trade_xyz_data_cycle_20260604_073932.log
wc -l data/raw/quotes/trade_xyz/2026-06-04.jsonl
ls -lh data/raw/quotes/trade_xyz/2026-06-04.jsonl
```

正常な途中状態:

```text
ps -fp 2484910 が process を返す
raw quote JSONL の mtime が新しい
raw quote row count が増える
log に fatal error がない
```

この状態なら何もしない。手動でcollectorをkillしない。

## 2. 予定時刻より前に止まった場合

PID が消えていたら、すぐに次cycleを起動しない。まず原因を見る。

```bash
ps -fp 2484910 || true
tail -120 logs/trade_xyz_data_cycle/trade_xyz_data_cycle_20260604_073932.log
uv run sis trade-xyz-collection-status --strict
```

見る項目:

```text
log:
  Traceback
  error
  finished
  lock
  stale

status:
  collector_running
  latest_raw_file_age_minutes
  progress_status
  failing_requirements
  known_gap_requirements
```

判断:

```text
正常終了:
  「3. 完了後のstatus再判定」へ進む

明確な一時API失敗:
  logのerrorと該当commandを残してから、同じcycleを再起動するか判断

lockだけ残った:
  trade-xyz-collection-status の lock fields を見て stale か確認
  stale lock は wrapper 側が回復できる設計だが、非空lockや実processがある場合は重複起動しない

原因不明:
  data/reports/trade_xyz_collection_status.md と log を読む
  次cycleを急いで起動しない
```

## 3. 完了後のstatus再判定

collector が終了したら、status / readiness を更新する。

```bash
uv run sis trade-xyz-collection-status --strict
```

最終gateとしては、まだreadyでないことを明示的に検出する場合にこれを使う。

```bash
uv run sis trade-xyz-collection-status --strict --fail-on-not-ready
```

見る項目:

```text
backtest_data_ready
readiness_decision
fail_count
known_gap_count
failing_requirements
known_gap_requirements
coverage_min_span_days
coverage_max_remaining_days_exact
coverage_completion_ratio_by_span
latest_raw_file_age_minutes
progress_status
signal_candles_status
signal_candles_request_error_count
real_market_reference_status
oracle_timestamp_provenance_status
account_specific_fee_status
```

完了条件:

```text
strict ready:
  uv run sis trade-xyz-collection-status --strict --fail-on-not-ready
  が exit 0

まだ完了ではない:
  backtest_data_ready=false
  readiness_decision=NOT_READY
  failing_requirements に quote_coverage が残る
```

`backtest_data_ready=true` は、strict status gate が通るまで宣言しない。

## 4. status別の次アクション

### quote_coverage だけが fail

次の24時間 cycle を回す。signal candles が pass のままなら、quote coverage を優先して skip してよい。

```bash
stamp="$(date -u +%Y%m%d_%H%M%S)"
mkdir -p .tmp/launchers
setsid -f zsh -lc "cd /home/tn/projects/marketlens-strike && env SIS_TRADE_XYZ_CYCLE_DURATION_MINUTES=1440 SIS_TRADE_XYZ_CYCLE_INTERVAL_SECONDS=60 SIS_TRADE_XYZ_CYCLE_SYMBOLS=AAPL,AMD,AMZN,EWJ,GOOGL,META,MSFT,NVDA,SP500,TSLA,XYZ100 SIS_TRADE_XYZ_CYCLE_COLLECT_SIGNAL_CANDLES=0 SIS_TRADE_XYZ_CYCLE_REFRESH_REGISTRY=1 scripts/collect_trade_xyz_data_cycle.sh >> .tmp/launchers/trade_xyz_data_cycle_${stamp}.setsid.log 2>&1"
```

起動後に確認する。

```bash
pgrep -af "scripts/collect_trade_xyz_data_cycle.sh"
ls -lt logs/trade_xyz_data_cycle | head
tail -40 "logs/trade_xyz_data_cycle/$(ls -t logs/trade_xyz_data_cycle | head -1)"
```

### signal_candles が fail

今回の hardening 後は、readiness の next action が failed symbols / intervals のsubset再取得commandを出す。

まず status report / readiness manifest から command を読む。

```bash
uv run sis trade-xyz-collection-status --strict
python3 - <<'PY'
import json
from pathlib import Path

path = Path("data/manifests/trade_xyz_data_readiness_manifest.json")
manifest = json.loads(path.read_text())
for action in manifest.get("next_actions", []):
    if action.get("key") == "collect_signal_candles":
        print(action.get("command"))
PY
```

その command を優先する。

手動で見るべき manifest fields:

```text
data/manifests/trade_xyz_signal_candles_manifest.json

request_error_count
request_errors
failed_keys
retry_attempt_count
retry_success_count
preserved_existing_row_count
replaced_key_count
artifacts.raw_candle_errors_root
estimated_rate_limit_weight
```

注意:

```text
429 / timeout / schema mismatch:
  失敗として扱う。既存成功データを上書きしない。

正常な空payload:
  successful empty として扱う。その key の既存rowsは空に置き換わる。
```

### real_market_reference が fail

missing symbol を確認してから再収集する。

```bash
uv run sis collect-trade-xyz-real-market-reference --start 2026-05-31 --interval 1d
uv run sis trade-xyz-collection-status --strict
```

古い archive や 2026-05-30以前の reference artifact を現行ready判定へ戻さない。

### oracle_timestamp_provenance が残る

これは known gap として扱う。次の代替は禁止。

```text
recv_ts_ms を oracle_ts_ms にする
source_ts_ms を oracle_ts_ms にする
oracle_freshness_proxy を oracle_ts_ms の代替にする
```

oracle timestamp provenance を strict ready にするには、別途、根拠ある source を実装し、その provenance manifest と tests を追加する必要がある。

## 5. 次cycleを起動してよい条件

次の全てを満たす場合だけ起動する。

```text
現在の collector が終了している
data-cycle lock が stale でない、または wrapperが安全に回復できる状態
直近 status が更新済み
failing_requirements が quote_coverage だけ、または他failの対応方針が明確
signal_candles_request_error_count が 0、または failed subset 再取得を先に済ませる判断をしている
```

重複起動を避ける確認:

```bash
pgrep -af "scripts/collect_trade_xyz_data_cycle.sh" || true
uv run sis trade-xyz-collection-status --strict
```

## 6. 記録更新

次のどれかが起きたら、必ず記録を更新する。

```text
24h cycle が正常完了した
cycle が途中停止した
次cycleを起動した
readiness の failing_requirements が変わった
backtest_data_ready が true になった
oracle timestamp provenance の方針を変えた
```

更新先:

```text
docs/TRADE_XYZ_REAL_DATA_COLLECTION_CURRENT_RECORD_2026-06-01.md
plan/TRADE_XYZ_BACKTEST_REAL_DATA_INGESTION_HANDOFF_2026-06-01.md
.ai_memory/HANDOFF.md
```

ドキュメント更新時は Tokyo time を `YYYY-MM-DD_HH:mm JST` 形式で書く。

## 7. やってはいけないこと

```text
起動中 collector を理由なく kill する
collector が生きている状態で次cycleを重複起動する
2026-05-30以前の実データをready判定に戻す
archive download を費用承認なしに実行する
source_ts_ms / recv_ts_ms / client timestamp を oracle_ts_ms として偽装する
signal candles を fill snapshot として使う
real market reference を live execution data として扱う
wallet / signing / exchange write API へ進む
strict gate 前に backtest_data_ready=true と言う
```

## 8. 最短再開手順

明日以降に再開したら、まずこれを実行する。

```bash
cd /home/tn/projects/marketlens-strike
ps -fp 2484910 || true
tail -120 logs/trade_xyz_data_cycle/trade_xyz_data_cycle_20260604_073932.log
wc -l data/raw/quotes/trade_xyz/2026-06-04.jsonl
uv run sis trade-xyz-collection-status --strict
```

結果を見て、次のどちらかへ進む。

```text
collector still running:
  待つ

collector exited:
  status の failing_requirements を見て、
  quote_coverage だけなら次の24h cycleを起動する
```
