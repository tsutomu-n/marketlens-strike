# marketlens-strike live evidence 現状詳細

Status: historical snapshot. この文書は 2026-05-26 08:07 JST 時点の live evidence 状況記録であり、current repo status の正本ではない。現行判断は `docs/CURRENT_STATE.md` と `docs/OPERATIONS_RUNBOOK.md` を先に読む。

作成日時: 2026-05-26 08:07 JST
対象 repo: `/home/tn/projects/marketlens-strike`
対象作業: gTrade live evidence 実データ取得、2026-05-25 未取得原因の確定、2026-05-27 失敗防止策の登録

## 1. 結論

2026-05-25 に gTrade live evidence の実データが取得されなかった直接原因は、実行失敗ではなく、QQQ/SPY の参照市場である XNYS が 2026-05-25 に休場だったためである。

現行コードの planner は `QQQ`, `SPY`, `XAU` の 3 銘柄で重なる推奨 live window を選ぶ。2026-05-25 は XAU は取引可能だったが、QQQ/SPY が XNYS 休場扱いだったため、3 銘柄共通の次回 window は `2026-05-26 22:45 JST` になった。

現在は `2026-05-26 22:45 JST` の主実行、`22:50 JST` の backup guard、さらに `2026-05-27 01:10 JST` と `03:00 JST` の recovery watchdog を登録済みである。systemd timer と cron の両方を使い、単一経路の脱落で失敗しにくい状態にしている。

## 2. 現在時刻と実行前状態

確認時刻:

```text
2026-05-26T08:07:39+09:00
```

この時点では、まだ main run の開始時刻 `2026-05-26 22:45 JST` より前である。したがって `live_evidence_20260526_2245.log` や `live_evidence_20260526_2245.json` が存在しないことは正常であり、失敗とは判定しない。

worktree 状態:

```text
## main...origin/main
?? logs/
```

`logs/` は live evidence の予約ログ、guard ログ、manifest を含む実行アーティファクトである。現時点では未追跡として見えている。

## 3. 2026-05-25 に取得できなかった原因

### 3.1 実際に存在する 2026-05-25 manifest

存在する manifest:

```text
logs/live_evidence/manifests/live_evidence_20260525_125306.json
```

この manifest の主要値:

```json
{
  "run_id": "20260525_125306",
  "status": "completed",
  "requested_schedule_jst": null,
  "log_path": null,
  "started_at_utc": "2026-05-25T12:53:06Z",
  "finished_at_utc": "2026-05-25T12:53:07Z",
  "duration_minutes": 120,
  "metadata_interval_seconds": 60,
  "step_order": ["preflight"],
  "row_counts": {},
  "decision": null,
  "failure_summary": null
}
```

重要点:

- `step_order` は `preflight` のみ。
- `row_counts` は空。
- `requested_schedule_jst` は `null`。
- `log_path` は `null`。
- `decision` は `null`。

これは実データ収集 run ではなく、dry-run/preflight 相当の manifest である。5/25 の実収集ログは存在しない。

### 3.2 5/25 の市場判定

固定時刻で再現した判定では、2026-05-25 の QQQ/SPY は XNYS 休場のため次回 open が 2026-05-26 22:30 JST になる。

検証済み事実:

```text
2026-05-25 XNYS is_session=False
2026-05-26 XNYS is_session=True
```

planner 再現:

```text
2026-05-25T12:53:06+00:00 -> target_start_jst=2026-05-26T22:45:00+09:00
QQQ CLOSED recommended_start_jst=2026-05-26T22:45:00+09:00 recommended_end_jst=2026-05-27T04:30:00+09:00
SPY CLOSED recommended_start_jst=2026-05-26T22:45:00+09:00 recommended_end_jst=2026-05-27T04:30:00+09:00
XAU OPEN   recommended_start_jst=2026-05-25T07:10:00+09:00 recommended_end_jst=2026-05-30T05:50:00+09:00
```

XAU だけなら 5/25 に取引可能だった。しかし planner は `QQQ SPY XAU` の共通 window を選ぶため、QQQ/SPY が休場なら 5/25 は採用されない。

### 3.3 原因の分類

原因は以下の通り。

- 失敗ではない: 5/25 に main collection を起動して落ちたログは無い。
- データ欠損でもない: 5/25 は `QQQ/SPY/XAU` 共通 window の対象外だった。
- scheduling の仕様通り: `build_live_evidence_plan(["QQQ", "SPY", "XAU"])` が最も遅い `recommended_start_jst` を採用する。
- 実行すべき対象日は 5/25 ではなく、5/26 22:45 JST から 5/27 00:45 JST までの 120 分 window。

## 4. 現在登録されている実行経路

### 4.1 main scheduler

プロセス:

```text
PID 1191355
CMD bash scripts/schedule_live_evidence.sh 2026-05-26T22:45 120 60
STAT Ss
```

schedule launcher 出力:

```text
target_jst=2026-05-26 22:45:00 JST
wait_seconds=89486
duration_minutes=120
metadata_interval_seconds=60
log_path=logs/live_evidence/live_evidence_20260526_2245.log
```

main scheduler は `2026-05-26 22:45 JST` まで sleep し、その後以下を実行する。

```text
uv run python scripts/run_live_evidence.py \
  --duration-minutes 120 \
  --metadata-interval-seconds 60 \
  --run-id 20260526_2245 \
  --requested-schedule-jst "2026-05-26 22:45:00 JST" \
  --log-path logs/live_evidence/live_evidence_20260526_2245.log
```

期待される main artifacts:

- `logs/live_evidence/live_evidence_20260526_2245.log`
- `logs/live_evidence/manifests/live_evidence_20260526_2245.json`

### 4.2 22:50 backup guard

プロセス:

```text
PID 1205293
CMD bash .tmp/live_evidence_20260526_2245_guard.sh
STAT SNs
```

guard 初期ログ:

```text
[2026-05-25T13:13:52Z] guard started
primary_run_id=20260526_2245
backup_run_id=20260526_2245_backup
guard_jst=2026-05-26 22:50:00 JST
wait_seconds=88568
```

guard の役割:

- `2026-05-26 22:50 JST` まで待機する。
- main log に `Scheduled live evidence run starting` があれば終了する。
- main manifest が存在すれば終了する。
- どちらも無ければ backup run を開始する。
- `flock` により、guard が複数経路から起動しても一つだけ実行する。

backup run の期待 artifacts:

- `logs/live_evidence/live_evidence_20260526_2245_backup.log`
- `logs/live_evidence/manifests/live_evidence_20260526_2245_backup.json`

backup run の目的は「main scheduler が起動しなかった場合」に代替することであり、main が開始済みならデータを二重に取りに行かない。

### 4.3 systemd timer

登録済み timer:

```text
Tue 2026-05-26 22:50:00 JST marketlens-live-evidence-20260526-2245-guard.timer
Wed 2026-05-27 01:10:00 JST marketlens-live-evidence-20260527-0110-recovery.timer
Wed 2026-05-27 03:00:00 JST marketlens-live-evidence-20260527-0300-recovery.timer
```

役割:

- `22:50` timer は backup guard を再度起動する。常駐 guard が生きていれば `flock` により何もせず終了する。
- `01:10` timer は recovery watchdog を起動する。
- `03:00` timer は late recovery watchdog を起動する。

### 4.4 cron backup

登録済み crontab:

```cron
50 22 26 5 * /usr/bin/bash /home/tn/projects/marketlens-strike/.tmp/live_evidence_20260526_2245_cron_once.sh >> /home/tn/projects/marketlens-strike/logs/live_evidence/live_evidence_20260526_2245_cron.out 2>&1 # marketlens-live-evidence-20260526-2245-cron
10 1 27 5 * /usr/bin/bash /home/tn/projects/marketlens-strike/.tmp/live_evidence_20260527_recovery_watchdog.sh 0110 90 60 >> /home/tn/projects/marketlens-strike/logs/live_evidence/live_evidence_20260527_0110_recovery_cron.out 2>&1 # marketlens-live-evidence-20260527-recovery
0 3 27 5 * /usr/bin/bash /home/tn/projects/marketlens-strike/.tmp/live_evidence_20260527_recovery_watchdog.sh 0300 60 60 >> /home/tn/projects/marketlens-strike/logs/live_evidence/live_evidence_20260527_0300_recovery_cron.out 2>&1 # marketlens-live-evidence-20260527-recovery
15 4 27 5 * /usr/bin/bash /home/tn/projects/marketlens-strike/.tmp/live_evidence_20260527_cron_cleanup.sh >> /home/tn/projects/marketlens-strike/logs/live_evidence/live_evidence_20260527_cron_cleanup.out 2>&1 # marketlens-live-evidence-20260527-recovery
```

cron の役割:

- user systemd timer が落ちた場合の backup。
- 22:50 に backup guard。
- 01:10 と 03:00 に recovery watchdog。
- 04:15 に 20260527 recovery 用 cron entry を削除する cleanup。

## 5. recovery watchdog の設計

対象 script:

```text
.tmp/live_evidence_20260527_recovery_watchdog.sh
```

構文検査:

```text
bash -n .tmp/live_evidence_20260527_recovery_watchdog.sh
```

検査済みでエラーなし。

watchdog の判定対象 manifest:

- `logs/live_evidence/manifests/live_evidence_20260526_2245.json`
- `logs/live_evidence/manifests/live_evidence_20260526_2245_backup.json`
- `logs/live_evidence/manifests/live_evidence_20260527_0110_recovery.json`
- `logs/live_evidence/manifests/live_evidence_20260527_0300_recovery.json`

成功判定:

- `status` が `completed` または `completed_with_retries`
- かつ row count が 0 より大きい
- row count は `raw_quotes`, `pricing_rows_delta`, `sidecar_pricing` の最大値で判定

起動抑止:

- `pgrep -af "scripts/run_live_evidence.py|sis.live_evidence_runner"` で active runner がいれば新規 recovery は起動しない。
- `flock` により同一 recovery run の多重起動を防止する。

01:10 recovery:

```text
bash .tmp/live_evidence_20260527_recovery_watchdog.sh 0110 90 60
```

期待 artifacts:

- `logs/live_evidence/live_evidence_20260527_0110_recovery.log`
- `logs/live_evidence/manifests/live_evidence_20260527_0110_recovery.json`
- `logs/live_evidence/live_evidence_20260527_0110_recovery_watchdog.out`

03:00 recovery:

```text
bash .tmp/live_evidence_20260527_recovery_watchdog.sh 0300 60 60
```

期待 artifacts:

- `logs/live_evidence/live_evidence_20260527_0300_recovery.log`
- `logs/live_evidence/manifests/live_evidence_20260527_0300_recovery.json`
- `logs/live_evidence/live_evidence_20260527_0300_recovery_watchdog.out`

## 6. 現在の planner 出力

確認コマンド:

```bash
uv run python scripts/plan_live_evidence_run.py --duration-minutes 120 --metadata-interval-seconds 60
```

確認結果:

```text
venue=gtrade
symbols=QQQ SPY XAU
QQQ: market_status=CLOSED recommended_start_jst=2026-05-26T22:45:00+09:00 recommended_end_jst=2026-05-27T04:30:00+09:00
SPY: market_status=CLOSED recommended_start_jst=2026-05-26T22:45:00+09:00 recommended_end_jst=2026-05-27T04:30:00+09:00
XAU: market_status=OPEN recommended_start_jst=2026-05-26T07:10:00+09:00 recommended_end_jst=2026-05-27T05:50:00+09:00
target_start_jst=2026-05-26T22:45:00+09:00
schedule_spec_jst=2026-05-26T22:45
schedule_command=bash scripts/schedule_live_evidence.sh 2026-05-26T22:45 120 60
```

この出力は、現在の予約と一致している。

## 7. いつ何が起きるか

すべて JST。

| 時刻 | 経路 | 内容 | 成功時の主な artifact |
|---|---|---|---|
| 2026-05-26 22:45 | main scheduler | 120 分 live evidence collection 開始 | `live_evidence_20260526_2245.log`, `live_evidence_20260526_2245.json` |
| 2026-05-26 22:50 | backup guard | main が開始していなければ backup collection 開始 | `live_evidence_20260526_2245_backup.log`, `live_evidence_20260526_2245_backup.json` |
| 2026-05-27 00:45 | main 予定終了 | main が正常ならこの頃に manifest/report が揃う | main manifest/report |
| 2026-05-27 01:10 | recovery watchdog | main/backup 成功 manifest が無ければ 90 分 recovery | `live_evidence_20260527_0110_recovery.*` |
| 2026-05-27 03:00 | late recovery watchdog | まだ成功 manifest が無ければ 60 分 recovery | `live_evidence_20260527_0300_recovery.*` |
| 2026-05-27 04:15 | cron cleanup | recovery 用 cron entry を削除 | `live_evidence_20260527_cron_cleanup.out` |

## 8. 成功判定

一次成功判定:

- manifest が存在する。
- manifest の `status` が `completed` または `completed_with_retries`。
- manifest の row count が 0 より大きい。
- `failure_summary` が null または運用上許容可能。

確認コマンド例:

```bash
uv run python -m json.tool logs/live_evidence/manifests/live_evidence_20260526_2245.json
```

main manifest が無い場合は順に確認する。

```bash
uv run python -m json.tool logs/live_evidence/manifests/live_evidence_20260526_2245_backup.json
uv run python -m json.tool logs/live_evidence/manifests/live_evidence_20260527_0110_recovery.json
uv run python -m json.tool logs/live_evidence/manifests/live_evidence_20260527_0300_recovery.json
```

最終判定:

```bash
uv run sis phase-gate-review
uv run python -m json.tool data/ops/phase_gate_review_summary.json
```

見るべき値:

- `decision`
- `phase2_entry_allowed`
- `live_evidence_status`
- `live_evidence_decision`
- gTrade diagnostics
- stale rate
- tradable rate
- missing mark/index rate
- oracle age

## 9. 再開時の最短確認

再開直後は以下を実行する。

```bash
bash .tmp/live_evidence_20260526_2245_status.sh
```

この script は以下をまとめて確認する。

- 現在時刻
- main scheduler PID
- backup guard PID
- user systemd timer
- crontab
- live evidence log/manifest 一覧

その後、時刻に応じて判断する。

### 9.1 2026-05-26 22:45 より前

正常状態:

- PID `1191355` が生存。
- PID `1205293` が生存。
- systemd timer が 22:50/01:10/03:00 を指す。
- cron entry が 22:50/01:10/03:00/04:15 を含む。

この場合は待機する。

### 9.2 2026-05-26 22:45 から 00:45 の間

確認対象:

- `logs/live_evidence/live_evidence_20260526_2245.log`
- `logs/live_evidence/manifests/live_evidence_20260526_2245.json`

この時間帯は run が進行中の可能性があるため、manifest が `running` でも即失敗扱いしない。

### 9.3 2026-05-27 00:45 から 01:10 の間

main/backup の完了確認をする。成功 manifest が無ければ 01:10 recovery watchdog を待つ。

### 9.4 2026-05-27 01:10 から 04:15 の間

recovery watchdog の log/manifest を確認する。03:00 の second recovery があるため、01:10 側が失敗していても即手動介入せず、03:00 の結果も確認する。

### 9.5 2026-05-27 04:15 以降

すべての自動経路が完了している想定。manifest と phase gate を確認し、Phase 2 可否を判断する。

## 10. 残リスク

潰したリスク:

- 5/25 のような非取引日を失敗と誤認するリスク。
- main scheduler の sleep プロセスだけに依存するリスク。
- main scheduler が起動しない場合に実収集が行われないリスク。
- main/backup が起動後に失敗した場合に再試行が無いリスク。
- systemd timer だけ、または cron だけに依存するリスク。
- 多重起動で manifest が壊れるリスク。

残る外部リスク:

- マシン/VM が実行時刻に停止している。
- OS が suspend して cron/systemd timer が動かない。
- ネットワークが切断されている。
- gTrade 側 API/WebSocket が停止、遅延、仕様変更している。
- `uv` または `bun` の実行環境が壊れている。
- upstream データは取得できても stale_rate や oracle_age が gate 条件を満たさない。

残る運用リスク:

- `logs/` は未追跡なので、必要に応じて保存/提出方針を決める必要がある。
- recovery script は `.tmp` 配下の運用用スクリプトであり、恒久運用にするなら `scripts/` 配下への昇格とテスト追加が望ましい。
- cron cleanup は 2026-05-27 04:15 に recovery 用 cron entry を削除するが、systemd transient timer の履歴は user systemd 側に残る可能性がある。

## 11. 参照ファイル

実行/予約:

- `scripts/plan_live_evidence_run.py`
- `scripts/schedule_live_evidence.sh`
- `scripts/run_live_evidence.py`
- `src/sis/live_evidence_plan.py`
- `src/sis/market_calendar.py`

一回限りの運用補助:

- `.tmp/live_evidence_20260526_2245_guard.sh`
- `.tmp/live_evidence_20260526_2245_cron_once.sh`
- `.tmp/live_evidence_20260526_2245_status.sh`
- `.tmp/live_evidence_20260527_recovery_watchdog.sh`
- `.tmp/live_evidence_20260527_cron_cleanup.sh`

ログ/manifest:

- `logs/live_evidence/next_schedule_launcher.out`
- `logs/live_evidence/live_evidence_20260526_2245_guard.out`
- `logs/live_evidence/manifests/live_evidence_20260525_125306.json`

再開用正本:

- `.ai_memory/HANDOFF.md`

## 12. 現時点の実務判断

2026-05-25 の未取得は、休日カレンダーに基づく正常なスケジューリング結果であり、障害ではない。

2026-05-26 22:45 JST からの実収集については、main scheduler、backup guard、systemd timer、cron、recovery watchdog により、少なくとも以下の 4 段階の実行機会がある。

1. 2026-05-26 22:45 main run
2. 2026-05-26 22:50 backup guard
3. 2026-05-27 01:10 recovery run
4. 2026-05-27 03:00 late recovery run

次に人間または次セッションが行うべきことは、実行時刻後に manifest と phase gate を確認することである。実行時刻前に追加で手動実行する必要はない。
