<!--
作成日: 2026-06-05_07:55 JST
更新日: 2026-06-05_07:55 JST
-->

# Long Running Script Operation Runbook 2026-06-05

この文書は、今後この repo で同様の長時間 script / wrapper / supervisor を回すときに、起動前、実行中、自然終了、異常終了、再実行、引き継ぎで何を確認し、何を記録するかを汎用化した運用手順である。

## 適用範囲

対象:

```text
scripts/collect_trade_xyz_data_cycle.sh
scripts/collect_trade_xyz_data_until_ready.sh
uv run sis collect-trade-xyz-data-cycle
uv run sis trade-xyz-collection-status
将来追加する同種の長時間 collector / normalizer / finalize / supervisor script
```

この文書は、特定の script の実装や最新状態そのものではない。最終判断では必ず code、CLI help、log、status artifact、manifest、test を優先する。

この文書は read-only / paper / research 運用のためのもの。wallet、signing、live order、exchange write API、課金を伴う外部書き込みの許可にはならない。

## 基本原則

長時間 script を扱うときの原則:

```text
1. 起動前に既存process、lock、前回log、前回statusを確認する。
2. 1つの lock scope に対して同種のcollector/supervisorを重複起動しない。
3. 起動したら command、PID、開始時刻、想定終了時刻、log path、lock path、出力先を記録する。
4. 実行中は軽量確認を優先し、重いcoverage/readiness再計算を毎回走らせない。
5. 自然終了は「PIDが消えたこと」だけでは判定しない。
6. 自然終了後も readiness / backtest_data_ready は別途 strict refresh で確認する。
7. 異常終了や不明状態では、次cycleを起動する前に log、lock、子process、status artifact を読む。
8. ファイル日付や行数の直感ではなく、起動logと該当コードで partition ルールを確認する。
9. chat transcript ではなく repo 内の durable artifact と `.ai_memory/HANDOFF.md` に残す。
```

## 起動前チェック

最初に読むもの:

```bash
git status --short --branch --untracked-files=all
uv run sis --help
uv run sis trade-xyz-collection-status --no-refresh-coverage --no-refresh-readiness --strict
```

対象 script が wrapper の場合は、help だけでなく wrapper 本体も読む。

```bash
sed -n '1,260p' scripts/collect_trade_xyz_data_cycle.sh
sed -n '1,320p' scripts/collect_trade_xyz_data_until_ready.sh
```

既存 process と lock を確認する。

```bash
pgrep -af "collect-trade-xyz-data-cycle|collect_trade_xyz_data_cycle|collect_trade_xyz_data_until_ready|collect-trade-xyz-quotes" || true
find .tmp -maxdepth 2 -type f -name pid -print -exec cat {} \; 2>/dev/null || true
find .tmp -maxdepth 2 -type d -name '*trade_xyz*lock*' -print 2>/dev/null || true
```

起動前に決めて記録する値:

```text
cwd:
command:
detached or foreground:
expected duration:
expected natural finish:
lock path:
log path:
state path:
status artifact:
raw / normalized / manifest output roots:
required env vars:
known gaps allowed:
automatic restart allowed:
manual stop condition:
```

## 起動記録テンプレート

長時間 script を起動したら、次の形式で docs または `.ai_memory/HANDOFF.md` に残す。

```text
script run:
  purpose:
  cwd:
  command:
  launcher:
  detached:
  parent_pid:
  child_pids:
  started_at_utc:
  started_at_jst:
  expected_finish_jst:
  duration:
  interval:
  max_cycles:
  lock_path:
  log_path:
  state_path:
  output_roots:
  status_command_light:
  status_command_strict:
  natural_exit_marker:
  do_not_start_duplicate_until:
  known_gaps_at_start:
  external_prereqs_missing:
```

`setsid -f` でdetachした場合は、launcher stdout/stderr の redirect 先も残す。

```text
launcher_output:
  /tmp/<name>.nohup
```

## 実行中の軽量監視

実行中の基本確認:

```bash
ps -fp <parent_pid>
pgrep -af "<script-or-cli-pattern>" || true
tail -80 <log_path>
uv run sis trade-xyz-collection-status --no-refresh-coverage --no-refresh-readiness --strict
```

raw file が進捗証拠になる場合:

```bash
find <raw_root> -maxdepth 1 -type f -printf '%TY-%Tm-%Td %TH:%TM %s %p\n' | sort | tail -20
wc -l <raw_file>
```

ただし、raw file の日付分割や出力先は script ごとに違う。起動時刻、UTC/JST、該当コードを確認せずに「今日の日付fileが増えていないから停止」と判断しない。

状態JSONがある場合は、dashboardではなく JSON を読む。

```bash
jq '{
  decision,
  backtest_data_ready,
  failing_requirements: .readiness_requirements.fail,
  known_gap_requirements: .readiness_requirements.known_gap,
  collector_running: .collector_process.running,
  collector_process_count: .collector_process.process_count,
  latest_file_stale: .raw_quote_inventory.latest_file_stale,
  latest_file_age_seconds: .raw_quote_inventory.latest_file_age_seconds,
  progress_status: .progress_since_previous_status.status,
  cycle_lock_stale: .locks.cycle.stale,
  supervisor_lock_stale: .locks.supervisor.stale
}' data/ops/trade_xyz_collection_status.json
```

監視間隔の目安:

```text
短時間 script:
  終了予定時刻の直後に1回確認する。

数時間以上の collector:
  進捗確認は raw mtime / row count / no-refresh status を中心にする。

24h以上の collector:
  途中で何度も strict coverage refresh を回さない。
  終了後に strict refresh する。
```

## 自然終了の汎用条件

自然終了と判断するには、原則として次をすべて満たす。

```text
1. 起動時に記録した parent PID が消えている。
2. 同じ command family の子processが残っていない。
3. log に script 固有の完了markerがある。
4. wrapper / supervisor lock が残っていない、または stale でない。
5. status command または artifact validation が通る。
6. 期待される output / manifest / state artifact が更新されている。
7. 終了後の strict check で次の分岐判断ができる。
```

確認コマンド例:

```bash
ps -fp <parent_pid> || true
pgrep -af "<script-or-cli-pattern>" || true
tail -160 <log_path>
test ! -e <lock_path> && echo "lock=absent"
uv run sis trade-xyz-collection-status --strict
```

`PID がない` だけでは自然終了ではない。log marker、lock cleanup、status refresh の3点を合わせて見る。

## 異常終了または不明状態

次のどれかに当てはまる場合は、自然終了として扱わない。

```text
PID が消えているが完了markerがない
親PIDは消えたが子processだけ残っている
lock directory または pid file が残っている
status command が失敗する
latest file が stale
progress_status が warning
traceback / exception / non-zero exit がlogにある
出力artifactが期待時刻以降に更新されていない
row count は増えたが manifest / readiness が更新されていない
```

この状態では、重複起動や lock 手動削除を最初の対応にしない。先に読むもの:

```bash
tail -240 <log_path>
ls -la <lock_path> || true
cat <lock_path>/pid 2>/dev/null || true
pgrep -af "<script-or-cli-pattern>" || true
uv run sis trade-xyz-collection-status --no-refresh-coverage --no-refresh-readiness --strict
```

原因を分類してから対応する。

```text
process残り:
  親子関係、実command、raw mtimeを見る。killは最後の選択肢。

stale lock:
  pidが死んでいるか、wrapperが自動回復するlockか、非空lockかを確認する。

external prerequisite:
  AWS credentials、account fee user address、network、API rate limitなどを確認する。

data quality fail:
  failing_requirements / known_gap_requirements / manifest details を読む。

implementation bug:
  tracebackと最小再現commandを残し、focused testを追加して直す。
```

## 終了後の分岐

終了後は必ず strict status を更新する。

```bash
uv run sis trade-xyz-collection-status --strict
```

分岐:

```text
backtest_data_ready=true:
  ただちに宣言しない。
  strict status、readiness manifest、coverage manifest、known gap の残りを確認してから記録する。

failing_requirements が quote_coverage だけ:
  次cycleまたは until-ready supervisor に進んでよい。
  ただし既存collector / lock がないことを再確認する。

quote_coverage 以外の fail がある:
  自動ループさせない。
  該当 fail を先に修正、再取得、または明示的な known gap として判断する。

known_gap だけが残る:
  研究用途で許すか、実務 ready に必要かを分ける。
  known gap を成功扱いに読み替えない。
```

## 再実行と自動ループの判断

自動ループさせてよい条件:

```text
collector_running=false
同種の child process が残っていない
lock が absent または正常
前回logに自然終了markerがある
status refresh が成功している
自動継続対象の fail だけが残っている
```

自動ループさせない条件:

```text
前回終了理由が不明
完了markerがない
非coverage fail が残っている
external prerequisite が未設定で、次cycle起動前gateとして扱う設定になっている
lock が stale または非空
progress warning が解消していない
```

Trade[XYZ] quote coverage では、`quote_coverage` だけが fail の場合に `scripts/collect_trade_xyz_data_until_ready.sh` へ進む。`real_market_reference`、`signal_candles`、`funding_events`、`account_specific_fee`、`historical_archive_preflight` などが fail の場合は、先に原因を潰す。

## ドキュメント更新ルール

長時間 script を回したら、少なくとも次を更新する。

```text
.ai_memory/HANDOFF.md:
  再開時に最初に見る正本。PID、log、state、次action、禁止事項を書く。

docs/OPERATIONS_RUNBOOK.md:
  長期運用で今後も使う入口と代表commandを書く。

対象別 current doc:
  今回の判断、自然終了条件、次の分岐、未解決riskを書く。
```

文書には次を分けて書く。

```text
確認済み:
  実際に command / file / log / code で確認した事実。

推論:
  codeや設定から妥当に読めるが、まだ実行結果で確定していないこと。

未確認:
  まだ見ていない外部前提や、権限・credential・market状態に依存するもの。

禁止:
  重複起動、live write、fake timestamp、ready誤宣言など。
```

## 記録テンプレート

実行中snapshot:

```text
checked_at_jst:
parent_pid:
child_processes:
log_path:
latest_log_marker:
raw_files:
row_count:
mtime:
status_decision:
collector_running:
progress_status:
failing_requirements:
known_gap_requirements:
operator_decision:
```

終了snapshot:

```text
checked_at_jst:
parent_pid_present:
child_process_present:
completion_marker_present:
lock_state:
strict_status_command:
strict_status_result:
updated_artifacts:
remaining_failures:
remaining_known_gaps:
next_action:
```

異常snapshot:

```text
checked_at_jst:
symptom:
last_success_marker:
first_error_marker:
process_state:
lock_state:
latest_output_state:
status_command_result:
suspected_cause:
safe_next_step:
do_not_do:
```

## 具体例: PID 2484910

`2026-06-04_16:39 JST` に起動した `PID 2484910` の 24h Trade[XYZ] quote coverage cycle では、起動時の UTC 日付で raw path が固定される。

```text
started:
  2026-06-04T07:39:32Z

primary raw file:
  data/raw/quotes/trade_xyz/2026-06-04.jsonl
```

このため、JSTで `2026-06-05_09:00` を過ぎても、`2026-06-05.jsonl` が増えないことだけを停止扱いしない。

PID固有の自然終了条件:

```text
docs/TRADE_XYZ_DATA_CYCLE_NATURAL_EXIT_CONDITIONS_2026-06-05.md
```

## 完了条件

この汎用runbookが満たすべき完了条件:

```text
長時間scriptの起動前確認が明記されている
起動時に残すべき値が明記されている
実行中の軽量監視と重いrefreshの使い分けが明記されている
自然終了と異常終了を区別できる
終了後の strict refresh と次cycle判断が明記されている
自動ループさせてよい条件と止める条件が分かる
将来の同種scriptにも使えるテンプレートがある
```
