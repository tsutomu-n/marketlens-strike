<!--
作成日: 2026-06-04_20:20 JST
更新日: 2026-06-06_10:28 JST
-->

# Trade[XYZ] Quote Coverage User Decision Record 2026-06-04

この文書は、Trade[XYZ] の quote coverage 収集について、ユーザーが「今どう判断すればよいか」を短く確認するための記録である。実装者向けの詳細は [TRADE_XYZ_QUOTE_COVERAGE_NEXT_STEPS_2026-06-04.md](TRADE_XYZ_QUOTE_COVERAGE_NEXT_STEPS_2026-06-04.md) を読む。PID `2484910` の自然終了条件は [TRADE_XYZ_DATA_CYCLE_NATURAL_EXIT_CONDITIONS_2026-06-05.md](TRADE_XYZ_DATA_CYCLE_NATURAL_EXIT_CONDITIONS_2026-06-05.md) を読む。

現在の主経路 next action ではなく、Trade[XYZ] quote coverage 収集を主目的にしていた時点の historical / operational record として読む。現在の開発主経路は backtest-first / venue-neutral である。

## 結論

```text
いまは待つ。
起動中の collector は止めない。
次cycleも until-ready supervisor も、PID 2484910 が生きている間は起動しない。
```

理由は、現在の 24h read-only quote collector が動いており、raw quote file も増えているため。ここで別cycleを増やすと、重複収集、lock混乱、原因追跡不能のリスクが増える。

## 現在の確認済み状態

確認時刻:

```text
2026-06-04_22:04 JST
```

確認結果:

```text
collector PID:
  2484910

状態:
  alive

raw quote file:
  data/raw/quotes/trade_xyz/2026-06-04.jsonl

row count:
  3542

mtime:
  2026-06-04_22:03 JST

log:
  logs/trade_xyz_data_cycle/trade_xyz_data_cycle_20260604_073932.log
```

注意:

```text
row count と mtime は収集中なので変わり続ける。
今回の data-cycle は起動時のUTC日付で raw path を固定するため、まず data/raw/quotes/trade_xyz/2026-06-04.jsonl を見る。
log が開始行だけでも、raw file が増えていればそれだけで停止扱いしない。
```

## ユーザーが見るもの

collector が生きているか:

```bash
ps -fp 2484910
```

raw file が増えているか:

```bash
find data/raw/quotes/trade_xyz -maxdepth 1 -type f -name '2026-06-0[45].jsonl' -print -exec wc -l {} \;
```

status を更新するのは、collector が自然終了した後でよい:

```bash
uv run sis trade-xyz-collection-status --strict
```

## 判断表

```text
PID 2484910 が生きている:
  待つ。
  次cycleを起動しない。
  until-ready supervisor も起動しない。

PID 2484910 が自然終了した:
  uv run sis trade-xyz-collection-status --strict を実行する。
  failing_requirements を見る。

failing_requirements が quote_coverage だけ:
  scripts/collect_trade_xyz_data_until_ready.sh を使ってよい。

failing_requirements に quote_coverage 以外が混じる:
  自動ループさせない。
  その fail を先に直す。

backtest_data_ready=true になった:
  strict gate の証拠を確認してから記録する。
```

## いまやってよいこと

```text
起動中 collector を見守る
24h WS smoke artifact は SP500 / NVDA / XYZ100 まで確認済みなので、同じ artifact contract と failure handling の回帰確認だけに留める
ドキュメントと handoff を最新状態に保つ
```

2026-06-04_21:52 JST の追加調査結果:

```text
30日 quote coverage が未完でも進められる既知の実装・テスト項目は完了。
追加で今やるべきことは、新cycle起動ではなく collector の自然終了待ち。
PID 2484910 が止まった後に full status refresh を行い、quote_coverage だけ fail なら until-ready へ進む。
quote_coverage 以外の fail が混じる場合は、自動ループさせずそのfailを先に直す。
```

2026-06-04_21:58 JST の追加検証結果:

```text
./scripts/check は pass。
pytest は 828 passed。
collector PID 2484910 はまだ alive。
raw quote rows は 3487 まで増加中。
```

2026-06-04_22:04 JST の追加確認結果:

```text
trade-xyz-collection-status --no-refresh-coverage --no-refresh-readiness --strict は pass。
collector_running=true。
progress_status=collecting_ok。
raw inventory total は 20194 rows。
traceable rows は 20194。
malformed rows は 0。
missing symbol rows は 0。
11 symbols は全て入っている。
failing_requirements は quote_coverage だけ。
known_gap_requirements は oracle_timestamp_provenance だけ。
```

2026-06-04_22:11 JST の archive preflight 確認結果:

```text
uv run sis check-trade-xyz-historical-archive-preflight を実行。
status は fail。
return_code は 255。
理由は Unable to locate credentials。
historical archive backfill は AWS credentials 未設定のため今は使わない。
このfailは起動中 collector を止める理由にしない。
```

2026-06-04_22:17 JST の oracle timestamp 確認結果:

```text
uv run sis build-trade-xyz-reference-data を実行。
uv run sis build-trade-xyz-data-readiness を実行。
quote_logs_read_count は 20339。
oracle_ts_present_count は 0。
oracle_ts_missing_count は 20339。
oracle_ts_missing_rate は 1.0。
理由は asset_ctx_missing_oracle_timestamp_field。
readiness は NOT_READY のまま。
判断: 30日 quote coverage を待たずに確認できる oracle timestamp provenance は再確認済み。ただし解消はしていない。
```

2026-06-04_22:19 JST の account-specific fee 確認結果:

```text
data/manifests/trade_xyz_account_fee_manifest.json は存在する。
status は pass。
user_taker_fee_bps は 4.5。
user_maker_fee_bps は 1.5。
missing_fields は空。
ただし SIS_TRADE_XYZ_ACCOUNT_FEE_USER_ADDRESS は未設定。
そのため、現在の環境変数と同じuserのfeeかどうかは matches_configured_user=null。
判断: fee artifact はある。最終ready前に公開user addressを設定して同一user照合する余地だけが残る。
```

2026-06-04_22:23 JST の readiness 棚卸し:

```text
pass:
  reference_datasets
  funding_events
  real_market_reference
  signal_candles
  fee_snapshots
  account_specific_fee
  session_state

fail:
  quote_coverage

known_gap:
  oracle_timestamp_provenance

判断: 30日 quote coverage を待たずに確認できる readiness requirement は、現時点では確認済み。collector が生きている間に追加cycleやsupervisorは起動しない。
```

2026-06-04_22:28 JST の phase-gate-review 確認結果:

```text
uv run sis phase-gate-review は再実行後に完了。
decision は READ_ONLY_GO。
strict_validation_passed は True。
strict_validation_issue_count は 0。
phase2_entry_allowed は True。
read_only_collector_gate_passed は True。
execution_drift_classification_counts.P2_BLOCKER は 0。
execution_drift_classification_counts.LIVE_READINESS_BLOCKER は 5。
./scripts/check は 830 passed。
timeout 30 uv run sis validate-artifacts --strict は checked_files=12 / issues=0。
近接テストは 11 passed。JSONL validation が validator を行ごとに作らないことも固定済み。
判断: read-only/paper gate は通る。ただし live readiness blocker は残る。30日 quote coverage や backtest_data_ready=true の代替ではない。
```

## まだやらないこと

```text
collector を kill する
次の24h cycleを重複起動する
until-ready supervisor を今すぐ起動する
24h smoke 結果を strategy selection に使う
24h smoke metrics を性能評価に使う
24h smoke だけで backtest_data_ready=true と言う
source_ts_ms / recv_ts_ms を oracle_ts_ms として扱う
wallet / signing / exchange write に進む
```

## なぜループ治具を作ったか

新しい大きな仕組みは作っていない。既存の `scripts/collect_trade_xyz_data_until_ready.sh` を、次のように実務向けに堅くした。

```text
collector が動いている間:
  軽量監視だけする。
  重いcoverage再計算を毎回走らせない。

collector が止まった後:
  full status refresh を行う。
  quote_coverage だけが fail なら次cycleへ進む。
  quote_coverage 以外の fail があるなら exit 7 で止める。

記録:
  data/ops/trade_xyz_until_ready_supervisor_state.json に判断状態を書く。
```

この方針により、単純な待ち作業は自動化できるが、別の問題を自動ループで隠さない。

## 抜け漏れ確認

確認済み:

```text
REST quote coverage collector と 24h WS smoke artifact は別物。
REST quote coverage は readiness の本番判定に関係する。
24h WS smoke は実装配線の確認であり、readiness の代替ではない。
SP500 / NVDA / XYZ100 の smoke は pass したが、これは全11銘柄coverageや性能評価の証拠ではない。
collector が生きている間は、次cycleも supervisor も増やさない。
quote_coverage 以外の fail は自動ループさせない。
```

残るリスク:

```text
quote coverage はまだ30日要件に届いていない。
oracle timestamp provenance は known gap のまま。
account-specific fee artifact は 2026-06-04_22:19 JST に確認済みで status=pass。ただし現在のenvに公開user addressが無いため同一user照合は未確認。
archive preflight は 2026-06-04_22:11 JST に確認済みで、AWS credentials 未設定により fail。
row count と mtime は時間で変わるため、この文書の数値は 2026-06-04_22:04 JST のsnapshotである。
```

## 完了条件

この記録に関する完了条件:

```text
ユーザーが今待つべき理由を読める
ユーザーが見ればよいコマンドが分かる
PID終了後の分岐が分かる
自動ループしてよい条件と止める条件が分かる
backtest_data_ready を誤って宣言しない境界が分かる
```

次に見る文書:

```text
詳細計画:
  docs/TRADE_XYZ_QUOTE_COVERAGE_NEXT_STEPS_2026-06-04.md

運用runbook:
  docs/OPERATIONS_RUNBOOK.md

再開正本:
  .ai_memory/HANDOFF.md
```
