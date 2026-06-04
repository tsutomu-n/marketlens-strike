<!--
作成日: 2026-06-04_17:47 JST
更新日: 2026-06-04_18:45 JST
-->

# Trade[XYZ] Quote Coverage And 24h Backtest Smoke Next Steps 2026-06-04

この文書は、30日quote coverageを待つ間に、24時間WS実データで先に進める作業を固定するための運用計画である。

## 結論

採用方針:

```text
1. 起動中の24時間 read-only quote collector は止めない。
2. 30日 quote coverage gate は別枠で継続する。
3. その待ち時間で、24h WS artifact を使った ingest/backtest 配線検証を進める。
4. 24h smoke の結果を strategy selection / production readiness には使わない。
```

この方針で「待ち時間」を実装検証に使う。ただし、`backtest_data_ready=true` は strict gate が通るまで宣言しない。

## 現在の確認済み状態

確認時刻:

```text
2026-06-04_18:43 JST
```

起動中 collector:

```text
PID:
  2484910

child:
  sis collect-trade-xyz-data-cycle

command:
  uv run sis collect-trade-xyz-data-cycle
  --collection-config configs/trade_xyz_data_collection.yaml
  --duration-minutes 1440
  --interval-seconds 60
  --seed-path configs/instrument_registry.seed.json
  --symbols AAPL,AMD,AMZN,EWJ,GOOGL,META,MSFT,NVDA,SP500,TSLA,XYZ100
  --strict
  --skip-signal-candles

started:
  2026-06-04_16:39 JST

expected finish:
  2026-06-05_16:39 JST 前後

log:
  logs/trade_xyz_data_cycle/trade_xyz_data_cycle_20260604_073932.log

raw quote file:
  data/raw/quotes/trade_xyz/2026-06-04.jsonl
  2026-06-05_09:00 JST 以降は UTC日付が変わるため、
  data/raw/quotes/trade_xyz/2026-06-05.jsonl にも書かれる可能性がある
```

current status artifact:

```text
data/ops/trade_xyz_collection_status.json

generated_at:
  2026-06-04T07:38:04.720674+00:00

decision:
  COLLECT_MORE_QUOTES

backtest_data_ready:
  false

readiness_decision:
  NOT_READY

fail_count:
  1

known_gap_count:
  1

注意:
  この status artifact は collector 起動直前のsnapshotであり、process状態は古い可能性がある。
  collector_running などを判断する前に trade-xyz-collection-status を再実行する。
```

24h WS normalized artifact:

```text
manifest:
  .tmp/trade_xyz_ws_quotes_24h.manifest.json

parquet:
  .tmp/trade_xyz_ws_quotes_24h.parquet

duckdb:
  .tmp/trade_xyz_ws_quotes_24h.duckdb

raw root:
  data/raw/ws/trade_xyz_24h_20260602_1902

symbols:
  NVDA
  SP500
  XYZ100

quote_count_written:
  1113529

bbo_quote_count:
  861859

active_asset_ctx_quote_count:
  251670
```

24h WS smoke backtest artifact:

```text
run_dir:
  .tmp/backtests_ws_24h/trade-xyz-smoke-SP500-1h-mid_price-source_ts_ms-ws_bbo_state

input_data_ref:
  .tmp/trade_xyz_ws_quotes_24h.parquet

symbol:
  SP500

timeframe:
  1h

entry_lookback:
  2

exit_lookback:
  2

trade_count:
  5

net_return_after_cost:
  -0.0009731640906773809

max_drawdown:
  -0.0011721687793645463

fee_row_resolved_rate:
  1.0

open_position_at_end:
  false

smoke_only:
  true

usable_for_strategy_selection:
  false

no_live_order:
  true

wallet_used:
  false

exchange_write_used:
  false
```

## 用語と責任境界

### 24h smoke

意味:

```text
24時間程度の実データで、raw -> normalized -> bar -> run_backtest artifact の配線が壊れていないことを確認する作業。
```

使ってよい用途:

```text
ingest code の回帰確認
bar builder の入力列確認
BBO fill snapshot と activeAssetCtx state の分離確認
no-lookahead join の確認
fee row resolution の確認
artifact writer の確認
report / manifest の生成確認
```

使ってはいけない用途:

```text
strategy selection
performance claim
production readiness
wallet / signing / exchange write readiness
backtest_data_ready=true 宣言
30日 quote coverage gate の代替
```

### 30日 quote coverage

意味:

```text
readiness gate 上の quote_coverage 要件。
現行 manifest は min_days_required=30.0 を要求する。
```

現在の扱い:

```text
待つ対象。
24h smoke が成功しても、この gate は解消しない。
```

### oracle timestamp provenance

意味:

```text
oracle_ts_ms が、source payload 内の根拠ある oracle timestamp field から来ているかを確認する gate。
```

現在の扱い:

```text
known gap。
recv_ts_ms / source_ts_ms / client timestamp で埋めない。
```

## 実行計画

### Phase A: 起動中 collector を安全に見守る

目的:

```text
現在走っている24時間 cycle を完走させる。
```

確認コマンド:

```bash
ps -fp 2484910
pstree -ap 2484910 || true
pgrep -af "collect-trade-xyz-data-cycle|collect_trade_xyz_data_cycle|collect-trade-xyz-quotes" || true
tail -80 logs/trade_xyz_data_cycle/trade_xyz_data_cycle_20260604_073932.log
find data/raw/quotes/trade_xyz -maxdepth 1 -type f -name '2026-06-0[45].jsonl' -print -exec wc -l {} \;
find data/raw/quotes/trade_xyz -maxdepth 1 -type f -name '2026-06-0[45].jsonl' -printf '%TY-%Tm-%Td %TH:%TM %s %p\n' | sort
```

正常な途中状態:

```text
PID 2484910 が存在する
子プロセスに sis collect-trade-xyz-data-cycle がある
raw quote JSONL の mtime が更新される
raw quote row count が増える
log に fatal error がない
```

注意:

```text
このcycleは UTC日付をまたぐ。
2026-06-05_09:00 JST 以降に 2026-06-04.jsonl の行数が止まっても、
2026-06-05.jsonl が増えているなら正常な可能性が高い。
```

やらないこと:

```text
collector を理由なく kill しない
collector が生きている状態で次cycleを重複起動しない
lock directory を手動削除しない
```

running中に status を見たい場合は、重いcoverage再計算を毎回走らせず、必要最小限にする。

```bash
uv run sis trade-xyz-collection-status --no-refresh-coverage --refresh-readiness --strict
```

ただし、この command も `data/ops/trade_xyz_collection_status.json` と report を書き換える。raw行数だけ見たい時は shell commands で十分。

受け入れ条件:

```text
log に finished が出る
PID が自然終了する
trade-xyz-collection-status を再実行できる
```

### Phase B: 24h WS smoke artifact を開発検証に使う

目的:

```text
30日coverageを待たずに、ingest/backtest 周辺の実装品質を上げる。
```

現在使える artifact:

```text
.tmp/trade_xyz_ws_quotes_24h.parquet
.tmp/trade_xyz_ws_quotes_24h.manifest.json
.tmp/backtests_ws_24h/trade-xyz-smoke-SP500-1h-mid_price-source_ts_ms-ws_bbo_state/
```

再実行コマンド:

```bash
uv run python scripts/run_trade_xyz_backtest_smoke.py \
  --input .tmp/trade_xyz_ws_quotes_24h.parquet \
  --funding-events '' \
  --symbol SP500 \
  --timeframe 1h \
  --event-time-source source_ts_ms \
  --out .tmp/backtests_ws_24h \
  --entry-lookback 2 \
  --exit-lookback 2 \
  --ws-bbo-state
```

検証する観点:

```text
raw_ws_root と input_data_ref が追跡可能
BBO rows だけが fill snapshot candidate になる
activeAssetCtx rows は state として no-lookahead join される
activeAssetCtx の source_ts_ms=None で落ちない
recv_ts_ms を oracle_ts_ms として使っていない
fills.parquet が生成される
metrics.json が生成される
backtest_run.json に smoke_only=true が残る
usable_for_strategy_selection=false が残る
no_live_order=true / wallet_used=false / exchange_write_used=false が残る
```

近接テスト:

```bash
uv run pytest -q tests/backtest/test_real_quotes_smoke.py tests/backtest/test_trade_xyz_ws_ingestion.py
```

広めの検証:

```bash
./scripts/check
```

受け入れ条件:

```text
実データ smoke が exit 0
fills.parquet / metrics.json / data_manifest.json / backtest_report.md が生成される
fee_row_resolved_rate が 1.0
open_position_at_end が false
smoke_only=true
usable_for_strategy_selection=false
./scripts/check が pass
```

### Phase C: 24h smoke で見つけるべき改善点

優先して見るもの:

```text
1. timestamp boundary
   source_ts_ms がある行とない行の分離
   recv_ts_ms の用途が observation time に限定されているか

2. fill boundary
   BBO 以外が exec_buy_price / exec_sell_price を作っていないか
   activeAssetCtx / trades が fill snapshot として混ざっていないか

3. state join
   activeAssetCtx state が未来参照なしで bar に付くか
   state_observed_ts_ms が bar event_ts を超えていないか

4. artifact contract
   manifest に input_data_ref / input hash / policy が残るか
   smoke artifact が production artifact と誤読されないか

5. failure handling
   source_ts_ms=None で落ちないか
   empty symbol / empty BBO / malformed row の error message が明確か
```

後回しにするもの:

```text
strategy performance tuning
parameter optimization
multi-strategy selection
live order simulation
wallet / signing / exchange write
```

### Phase D: 24h collector 完了後に status を更新する

collector が自然終了したら実行する:

```bash
uv run sis trade-xyz-collection-status --strict
```

wrapperは正常終了時に `uv run sis trade-xyz-collection-status` を呼ぶが、再開者は自分の時点で再実行してよい。`data/ops/trade_xyz_collection_status.json` は古い可能性があるため、JSONを読む前に status command を実行する。

ready 判定を明示的に確認する:

```bash
uv run sis trade-xyz-collection-status --strict --fail-on-not-ready
```

CLI stdout / reportで見る項目:

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

JSON artifactを直接見る場合は、nested path を使う。

```bash
jq '{
  decision,
  backtest_data_ready,
  readiness_decision,
  fail_count,
  known_gap_count,
  failing_requirements: .readiness_requirements.fail,
  known_gap_requirements: .readiness_requirements.known_gap,
  collector_running: .collector_process.running,
  collector_process_count: .collector_process.process_count,
  cycle_lock_stale: .locks.cycle.stale,
  supervisor_lock_stale: .locks.supervisor.stale,
  coverage_min_span_days: .coverage.min_span_days,
  coverage_max_remaining_days_exact: .coverage.max_remaining_days_exact,
  coverage_completion_ratio_by_span: .coverage.completion_ratio_by_span,
  latest_file_age_seconds: .raw_quote_inventory.latest_file_age_seconds,
  progress_status: .progress_since_previous_status.status,
  signal_candles_status: .readiness_requirement_details.signal_candles.status,
  signal_candles_request_error_count: .readiness_requirement_details.signal_candles.request_error_count,
  real_market_reference_status: .readiness_requirement_details.real_market_reference.status,
  oracle_timestamp_provenance_status: .readiness_requirement_details.oracle_timestamp_provenance.status,
  account_specific_fee_status: .readiness_requirement_details.account_specific_fee.status
}' data/ops/trade_xyz_collection_status.json
```

想定される結果:

```text
quote_coverage はまだ fail の可能性が高い。
この場合は backtest_data_ready=false のまま、次の24h cycleを検討する。
```

### Phase E: 次の24h cycle を起動する

次の全てを満たす場合だけ起動する:

```text
現在の collector が終了している
data-cycle lock が stale でない、または wrapper が安全に回復できる状態
直近 status が更新済み
failing_requirements が quote_coverage だけ、または他failの対応方針が明確
signal_candles_request_error_count が 0、または failed subset 再取得を先に済ませる判断をしている
```

重複起動を避ける確認:

```bash
pgrep -af "collect-trade-xyz-data-cycle|collect_trade_xyz_data_cycle|collect-trade-xyz-quotes" || true
uv run sis trade-xyz-collection-status --strict
```

起動コマンド:

```bash
stamp="$(date -u +%Y%m%d_%H%M%S)"
mkdir -p .tmp/launchers
setsid -f zsh -lc "cd /home/tn/projects/marketlens-strike && env SIS_TRADE_XYZ_CYCLE_DURATION_MINUTES=1440 SIS_TRADE_XYZ_CYCLE_INTERVAL_SECONDS=60 SIS_TRADE_XYZ_CYCLE_SYMBOLS=AAPL,AMD,AMZN,EWJ,GOOGL,META,MSFT,NVDA,SP500,TSLA,XYZ100 SIS_TRADE_XYZ_CYCLE_COLLECT_SIGNAL_CANDLES=0 SIS_TRADE_XYZ_CYCLE_REFRESH_REGISTRY=1 scripts/collect_trade_xyz_data_cycle.sh >> .tmp/launchers/trade_xyz_data_cycle_${stamp}.setsid.log 2>&1"
```

起動後確認:

```bash
pgrep -af "collect-trade-xyz-data-cycle|collect_trade_xyz_data_cycle|collect-trade-xyz-quotes"
latest_log="$(ls -t logs/trade_xyz_data_cycle/*.log | head -1)"
printf 'latest_log=%s\n' "${latest_log}"
tail -40 "${latest_log}"
```

起動したら、PID、log path、起動時刻を `docs/TRADE_XYZ_REAL_DATA_COLLECTION_CURRENT_RECORD_2026-06-01.md` と `.ai_memory/HANDOFF.md` に残す。

## status別アクション

### quote_coverage だけが fail

行動:

```text
次の24h cycle を回す。
同時に 24h smoke artifact で backtest 周辺の検証を続ける。
```

### signal_candles が fail

行動:

```text
readiness manifest の next action を優先する。
failed symbols / intervals の subset 再取得を先に行う。
```

確認:

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

### real_market_reference が fail

行動:

```text
missing symbol を確認してから再収集する。
古い archive や 2026-05-30以前の reference artifact を現行ready判定へ戻さない。
```

再収集例:

```bash
uv run sis collect-trade-xyz-real-market-reference --start 2026-05-31 --interval 1d
uv run sis trade-xyz-collection-status --strict
```

### oracle_timestamp_provenance が残る

行動:

```text
known gap として扱う。
```

禁止:

```text
recv_ts_ms を oracle_ts_ms にする
source_ts_ms を oracle_ts_ms にする
oracle_freshness_proxy を oracle_ts_ms の代替にする
```

strict ready にする条件:

```text
根拠ある oracle timestamp source を実装する
provenance manifest を更新する
tests を追加する
recv/source/client timestamp の流用でないことを確認する
```

## 記録更新ルール

次のどれかが起きたら記録を更新する:

```text
24h cycle が正常完了した
cycle が途中停止した
次cycleを起動した
readiness の failing_requirements が変わった
24h smoke artifact の入力・出力・検証結果が変わった
backtest_data_ready が true になった
oracle timestamp provenance の方針を変えた
```

更新先:

```text
docs/TRADE_XYZ_REAL_DATA_COLLECTION_CURRENT_RECORD_2026-06-01.md
plan/TRADE_XYZ_BACKTEST_REAL_DATA_INGESTION_HANDOFF_2026-06-01.md
docs/TRADE_XYZ_QUOTE_COVERAGE_NEXT_STEPS_2026-06-04.md
.ai_memory/HANDOFF.md
```

ドキュメント更新時は Tokyo time を `YYYY-MM-DD_HH:mm JST` 形式で書く。

## やってはいけないこと

```text
起動中 collector を理由なく kill する
collector が生きている状態で次cycleを重複起動する
2026-05-30以前の実データをready判定に戻す
archive download を費用承認なしに実行する
source_ts_ms / recv_ts_ms / client timestamp を oracle_ts_ms として偽装する
signal candles を fill snapshot として使う
activeAssetCtx / trades を fill snapshot として使う
real market reference を live execution data として扱う
wallet / signing / exchange write API へ進む
strict gate 前に backtest_data_ready=true と言う
24h smoke metrics を strategy selection に使う
```

## 最短再開手順

再開したら、まずこれを実行する:

```bash
cd /home/tn/projects/marketlens-strike
ps -fp 2484910 || true
pstree -ap 2484910 || true
tail -120 logs/trade_xyz_data_cycle/trade_xyz_data_cycle_20260604_073932.log
find data/raw/quotes/trade_xyz -maxdepth 1 -type f -name '2026-06-0[45].jsonl' -print -exec wc -l {} \;
uv run sis trade-xyz-collection-status --strict
```

分岐:

```text
collector still running:
  待つ。
  並行して 24h WS smoke artifact を使った ingest/backtest 検証を進める。

collector exited:
  status の failing_requirements を見る。
  quote_coverage だけなら次の24h cycleを起動する。

smoke artifact を再確認したい:
  scripts/run_trade_xyz_backtest_smoke.py --ws-bbo-state を再実行する。
```

## 抜け・漏れ・誤謬リスク確認

確認済み:

```text
24h smoke は backtest_data_ready ではない
30日 quote coverage は別 gate
oracle timestamp provenance は known gap
BBO と activeAssetCtx の責任境界は分離
live / wallet / signing / exchange write は範囲外
collector 重複起動は禁止
```

残るリスク:

```text
collector が途中停止した場合、status更新前に次cycleを起動すると原因が見えにくくなる
2026-06-05_09:00 JST 以降はUTC日付が変わるため、2026-06-04.jsonlだけを見ると収集停止と誤認する
古い data/ops/trade_xyz_collection_status.json をそのまま読むと collector process 状態を誤認する
24h smoke metrics は少数取引なので性能評価に使うと誤解を生む
archive backfill は requester-pays / AWS preflight のリスクがあるため、費用承認なしに進めない
oracle timestamp は source payload に根拠がない限り解消しない
```
