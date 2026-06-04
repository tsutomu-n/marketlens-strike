<!--
作成日: 2026-06-05_07:40 JST
更新日: 2026-06-05_07:55 JST
-->

# Trade[XYZ] Data Cycle Natural Exit Conditions 2026-06-05

この文書は、`PID 2484910` で動いている `scripts/collect_trade_xyz_data_cycle.sh` が「自然終了した」と判断できる条件、正常な終了手順、異常終了との見分け方、終了後の操作を固定するための運用記録である。

## 結論

`PID 2484910` の自然終了条件は、起動済みの 24h data-cycle が `--duration-minutes 1440 --interval-seconds 60` の収集loopを最後まで実行し、その後の bundle/readiness/status 更新まで完了して、wrapper log に `Trade[XYZ] data cycle finished` が出ることである。

自然終了は `backtest_data_ready=true` を意味しない。自然終了後に strict status を再実行し、残る fail が `quote_coverage` だけかどうかを別途確認する。

## 現在の確認済みsnapshot

確認時刻:

```text
2026-06-05_07:39 JST
```

確認結果:

```text
PID:
  2484910

状態:
  alive

親wrapper:
  bash scripts/collect_trade_xyz_data_cycle.sh

子process:
  uv run sis collect-trade-xyz-data-cycle
  .venv/bin/sis collect-trade-xyz-data-cycle

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
  2026-06-04_16:39:32 JST
  2026-06-04T07:39:32Z

expected natural finish:
  2026-06-05_16:39 JST 前後
  後処理ぶん数分ずれる可能性あり

log:
  logs/trade_xyz_data_cycle/trade_xyz_data_cycle_20260604_073932.log

current raw quote file:
  data/raw/quotes/trade_xyz/2026-06-04.jsonl

row count at snapshot:
  9823

mtime at snapshot:
  2026-06-05_07:39 JST
```

## なぜ 2026-06-04.jsonl に書き続けるか

今回の data-cycle は `collect_trade_xyz_quote_window()` を使う。この実装は、起動時の `started.date()` で raw path を一度だけ決める。

```text
started:
  2026-06-04T07:39:32Z

raw path:
  data/raw/quotes/trade_xyz/2026-06-04.jsonl
```

したがって、今回の `PID 2484910` については、JSTで `2026-06-05_09:00` を過ぎても raw path は原則 `2026-06-04.jsonl` のままである。`2026-06-05.jsonl` が増えないことだけを停止扱いしない。

確認対象はまずこれ。

```bash
find data/raw/quotes/trade_xyz -maxdepth 1 -type f -name '2026-06-04.jsonl' -printf '%TY-%Tm-%Td %TH:%TM %s %p\n' -exec wc -l {} \;
```

将来の別collector、別wrapper、archive normalize、または実装変更では日付分割が変わり得る。その場合は起動log、status artifact、該当コードを優先する。

## 自然終了までに実行される処理

### 1. wrapper 起動

入口:

```text
scripts/collect_trade_xyz_data_cycle.sh
```

主な設定:

```text
DURATION_MINUTES=1440
INTERVAL_SECONDS=60
COLLECTION_CONFIG=configs/trade_xyz_data_collection.yaml
LOCK_DIR=.tmp/trade_xyz_data_cycle.lock
COLLECT_SIGNAL_CANDLES=0
ALLOW_KNOWN_GAPS=0
REFRESH_REGISTRY=1
```

wrapper は `.tmp/trade_xyz_data_cycle.lock` を作り、`pid` に wrapper PID を書く。既存processがいる場合は重複起動を拒否する。

### 2. CLI 実行

wrapper は次を実行する。

```text
uv run sis collect-trade-xyz-data-cycle
```

今回の有効option:

```text
--duration-minutes 1440
--interval-seconds 60
--symbols AAPL,AMD,AMZN,EWJ,GOOGL,META,MSFT,NVDA,SP500,TSLA,XYZ100
--strict
--skip-signal-candles
```

`--strict` は known gap を完了扱いしないという意味であり、`backtest_data_ready=false` なら即プロセス失敗にするという意味ではない。

### 3. quote window loop

実装:

```text
src/sis/venues/trade_xyz/collector.py
collect_trade_xyz_quote_window()
```

iteration数:

```text
int((duration_minutes * 60) / interval_seconds)
= int((1440 * 60) / 60)
= 1440
```

各iterationで行うこと:

```text
1. Trade[XYZ] /info allMids を読む
2. Trade[XYZ] /info metaAndAssetCtxs を読む
3. 対象11symbolの quote rows を raw JSONL にappendする
4. 最終iteration以外は interval_seconds=60 秒 sleep する
```

理論上の新規row数の目安:

```text
1440 iterations * 11 symbols = 15840 rows
```

ただし、API失敗、既存同日fileへのappend、schema skip、対象symbol解決の差分があるため、最終row countをこの数に完全一致させる必要はない。自然終了の判定は row count 一致ではなく、プロセス完了、log、status refresh、lock cleanup で行う。

### 4. collection bundle / readiness 更新

quote window の後、CLI は bundle/readiness 系のartifactを更新する。

今回の重要な境界:

```text
signal candles:
  --skip-signal-candles のため、このcycleでは再取得しない。

real-market reference:
  CLI defaultでは collect_real_market_reference_data=true。
  既存設定とcache状態に従って bundle 側で扱われる。

account fee:
  --account-fee-user-address が渡っていないため、このcycleでは新しい userFees 取得はしない。

readiness:
  quote coverage / funding / session / fee / real-market / oracle provenance などを再評価する。
```

### 5. wrapper 後処理

CLI が正常終了した後、wrapper は追加で次を実行する。

```text
uv run sis trade-xyz-collection-status
```

その後、log に次を出す。

```text
Trade[XYZ] data cycle finished
```

wrapper は `trap` で `.tmp/trade_xyz_data_cycle.lock/pid` を削除し、空になった lock directory を削除する。

## 自然終了と判断できる条件

自然終了と判断するには、次をすべて満たす。

```text
1. ps -fp 2484910 が process を返さない
2. pgrep で collect-trade-xyz-data-cycle / collect_trade_xyz_data_cycle の実processが残っていない
3. logs/trade_xyz_data_cycle/trade_xyz_data_cycle_20260604_073932.log に Trade[XYZ] data cycle finished がある
4. .tmp/trade_xyz_data_cycle.lock が残っていない
5. uv run sis trade-xyz-collection-status --strict が実行できる
```

確認コマンド:

```bash
ps -fp 2484910 || true
pgrep -af "collect-trade-xyz-data-cycle|collect_trade_xyz_data_cycle|collect-trade-xyz-quotes" || true
tail -120 logs/trade_xyz_data_cycle/trade_xyz_data_cycle_20260604_073932.log
test ! -e .tmp/trade_xyz_data_cycle.lock && echo "cycle_lock=absent"
uv run sis trade-xyz-collection-status --strict
```

status JSON で見るもの:

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
  progress_status: .progress_since_previous_status.status,
  latest_file_age_seconds: .raw_quote_inventory.latest_file_age_seconds
}' data/ops/trade_xyz_collection_status.json
```

## 自然終了ではない状態

次のどれかに当てはまる場合は、自然終了として扱わない。

```text
PID が消えているが、log に Trade[XYZ] data cycle finished が無い
子processだけが残っている
.tmp/trade_xyz_data_cycle.lock が残っている
lock の pid が死んでいる
status command が落ちる
latest raw file が stale
progress_status が warning
Python traceback がlogにある
```

この場合は、次cycleや until-ready supervisor を起動しない。まず log、lock、status artifact、raw file mtime を確認する。

確認コマンド:

```bash
tail -200 logs/trade_xyz_data_cycle/trade_xyz_data_cycle_20260604_073932.log
ls -la .tmp/trade_xyz_data_cycle.lock || true
cat .tmp/trade_xyz_data_cycle.lock/pid 2>/dev/null || true
uv run sis trade-xyz-collection-status --no-refresh-coverage --no-refresh-readiness --strict
```

## PID が予定時刻を過ぎても生きている場合

`2026-06-05_16:39 JST` を少し過ぎていても、後処理中の可能性がある。すぐに kill しない。

目安:

```text
16:39-16:50 JST:
  後処理中の可能性がある。process、log、raw mtimeを見る。

17:00 JST 以降:
  まだ生きていて raw mtime が止まっているなら調査する。
  それでも kill は最初の選択肢にしない。
```

軽量確認:

```bash
ps -fp 2484910
pgrep -af "collect-trade-xyz-data-cycle|collect_trade_xyz_data_cycle|collect-trade-xyz-quotes" || true
find data/raw/quotes/trade_xyz -maxdepth 1 -type f -name '2026-06-04.jsonl' -printf '%TY-%Tm-%Td %TH:%TM %s %p\n' -exec wc -l {} \;
uv run sis trade-xyz-collection-status --no-refresh-coverage --no-refresh-readiness --strict
```

## 自然終了後の分岐

### quote_coverage だけが fail

次の条件なら until-ready loop に進んでよい。

```text
collector_running=false
cycle lock が stale でない
failing_requirements が quote_coverage だけ
known_gap_requirements が既知の範囲に留まる
```

推奨:

```bash
setsid -f scripts/collect_trade_xyz_data_until_ready.sh >/tmp/trade_xyz_until_ready.nohup 2>&1 < /dev/null
```

### quote_coverage 以外も fail

自動ループさせない。

例:

```text
signal_candles
real_market_reference
funding_events
fee_snapshots
session_state
account_specific_fee
historical_archive_preflight
```

この場合は、その fail を先に調査し、原因を記録してから次の収集を判断する。

### backtest_data_ready=true

即宣言しない。strict status、readiness manifest、coverage manifest、known gap の残りを確認してから記録する。

確認:

```bash
uv run sis trade-xyz-collection-status --strict --fail-on-not-ready
jq '.backtest_data_ready, .readiness_decision, .readiness_requirements' data/ops/trade_xyz_collection_status.json
```

## やってはいけないこと

```text
PID 2484910 が生きている間に次cycleを起動する
PID 2484910 が生きている間に until-ready supervisor を起動する
log に finished が無いのに自然終了扱いする
lock が残っているのに手動削除だけして次cycleへ進む
source_ts_ms / recv_ts_ms を oracle_ts_ms に流用する
24h cycle 完了だけで backtest_data_ready=true と言う
read-only/paper gate pass を live trading ready と読む
```

## 完了条件

この文書で扱う終了確認の完了条件:

```text
自然終了の定義が明確
自然終了と異常終了を区別できる
raw file の日付誤認を避けられる
終了後の strict status refresh が明記されている
quote_coverage-only の時だけ until-ready へ進む
backtest_data_ready を誤って宣言しない
```

## 関連文書

```text
ユーザー向け判断:
  docs/TRADE_XYZ_QUOTE_COVERAGE_USER_DECISION_RECORD_2026-06-04.md

詳細計画:
  docs/TRADE_XYZ_QUOTE_COVERAGE_NEXT_STEPS_2026-06-04.md

運用runbook:
  docs/OPERATIONS_RUNBOOK.md

汎用長時間script運用:
  docs/LONG_RUNNING_SCRIPT_OPERATION_RUNBOOK_2026-06-05.md

再開正本:
  .ai_memory/HANDOFF.md
```
