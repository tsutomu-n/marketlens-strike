<!--
作成日: 2026-06-21_18:29 JST
更新日: 2026-07-06_18:03 JST
-->

# Crypto Perp Truth-Cycle Runbook

Crypto Perp Truth-Cycle の post-MVP 実務runbookです。目的は、candidate event を勝ち筋の物語に変えず、prospective decision、matured outcome、tournament report まで同じ手順で再生成することです。

このrunbookは自動売買、wallet、signing、exchange write、tiny live measurementの承認ではありません。

## 正本

- `src/sis/crypto_perp/`
- `src/sis/commands/crypto_perp.py`
- `src/sis/commands/crypto_perp_live.py`
- `schemas/crypto_perp_*.schema.json`
- `tests/crypto_perp/`
- `uv run sis --help`
- [../CURRENT_STATE.md](../CURRENT_STATE.md)
- [../IMPLEMENTED_SURFACES.md](../IMPLEMENTED_SURFACES.md)
- [../CURRENT_GOAL_AND_DIRECTION_2026-07-05.md](../CURRENT_GOAL_AND_DIRECTION_2026-07-05.md)
- [../NO_CASH_GOAL_PROGRESS_2026-07-05.md](../NO_CASH_GOAL_PROGRESS_2026-07-05.md)
- [../crypto_perp/BACKTEST_CANDIDATE_PACK_V1.md](../crypto_perp/BACKTEST_CANDIDATE_PACK_V1.md)
- [../crypto_perp/PROFIT_READINESS_SURFACE_INVENTORY_2026-06-27.md](../crypto_perp/PROFIT_READINESS_SURFACE_INVENTORY_2026-06-27.md)
- [../crypto_perp/PROFIT_READINESS_ACCEPTANCE_VOCABULARY.md](../crypto_perp/PROFIT_READINESS_ACCEPTANCE_VOCABULARY.md)

## P-1: actual cashなしのbacktest candidate packを作る

actual cash、tiny-live、live order を扱わず、既存 local artifact から timestamp-safe な simulation evidence を作る場合は、Backtest Candidate Pack v1 を生成します。

進捗は [../NO_CASH_GOAL_PROGRESS_2026-07-05.md](../NO_CASH_GOAL_PROGRESS_2026-07-05.md) を読みます。Backtest Candidate Pack の command が動くことと、証拠品質が十分であることは分けて扱います。

```bash
uv run sis crypto-perp-backtest-candidate-pack
```

生成先:

- `data/crypto_perp/backtest_candidate_pack/latest/signal_rows.jsonl`
- `data/crypto_perp/backtest_candidate_pack/latest/data_availability_ledger.json`
- `data/crypto_perp/backtest_candidate_pack/latest/execution_assumptions.json`
- `data/crypto_perp/backtest_candidate_pack/latest/no_lookahead_report.json`
- `data/crypto_perp/backtest_candidate_pack/latest/backtest_result.json`
- `data/crypto_perp/backtest_candidate_pack/latest/stress_result.json`
- `data/crypto_perp/backtest_candidate_pack/latest/decision.json`
- `data/crypto_perp/backtest_candidate_pack/latest/decision.md`

見るもの:

- `decision`
- `reason_codes`
- `summary.selected_action_counts`
- `summary.no_lookahead.failed_count`
- `summary.no_lookahead.unverified_count`

次に直接 Paper Observation へ進めず、no-cash backtest gate に通します。

```bash
uv run sis crypto-perp-no-cash-backtest-gate \
  --decision data/crypto_perp/backtest_candidate_pack/latest/decision.json \
  --data-availability data/crypto_perp/backtest_candidate_pack/latest/data_availability_ledger.json \
  --backtest data/crypto_perp/backtest_candidate_pack/latest/backtest_result.json \
  --stress data/crypto_perp/backtest_candidate_pack/latest/stress_result.json \
  --rolling-stability data/crypto_perp/backtest_candidate_pack/latest/rolling_stability_result.json \
  --out data/crypto_perp/no_cash_backtest_gate/latest
```

`NO_CASH_BACKTEST_HOLD` は human review に残すだけで、paper order permission ではありません。
- `summary.backtest.unknown_count`
- `boundary`
- `non_goal_flags`

止める条件:

- `decision=BACKTEST_COLLECT_MORE_DATA`
- `summary.no_lookahead.failed_count > 0`
- `summary.no_lookahead.unverified_count > 0`
- `summary.backtest.unknown_count > 0`
- `non_goal_flags.profit_proven=true`
- `boundary.permits_live_order=true`

この pack は simulation evidence です。`BACKTEST_CANDIDATE_HOLD` でも profit proof、actual cash readiness、paper permission、tiny-live readiness、live readiness ではありません。

## P00: tournament rows からreportを再生成する

fixture-onlyで status / Daily Brief / Workbench Viewer の読み味をまとめて確認する場合は、dogfood packを作ります。

```bash
uv run sis crypto-perp-truth-cycle-dogfood-pack \
  --out data/crypto_perp/truth_cycle_dogfood \
  --replace-existing
```

これは missing probe audit のfixture状態を作るだけです。public network、credential、wallet、signing、exchange write、live orderは使いません。

最初に `dogfood_pack.md` の `Review Order`、`Stop Decision`、`Next Steps` を読みます。fixture packで `MISSING_PROBE_AUDIT` が出る場合は、実runでも probe / probe audit artifact path を先に確認し、勝ち筋やtiny liveの話へ進めません。`Next Steps` の `network_allowed`、`exchange_write_allowed`、`live_order_allowed` は、このpackから何を許可していないかを確認するために読みます。

手元にあるartifactから次に何が欠けているかだけを見る場合は、先にstatusを作ります。

```bash
uv run sis crypto-perp-truth-cycle-status \
  --probe-audit data/crypto_perp/probe_audit/latest/probe_audit.json \
  --raw-refresh data/crypto_perp/raw_refresh/latest/raw_refresh.json \
  --source-availability data/crypto_perp/source_availability/latest/source_availability.json \
  --edge-score data/crypto_perp/edge_score/latest/edge_score.json \
  --rows-v2 data/crypto_perp/tournament_rows_v2/latest/tournament_rows_v2.json \
  --bias-guard data/crypto_perp/bias_guard/latest/bias_guard.json \
  --out data/crypto_perp/truth_cycle_status/latest
```

生成物:

- `truth_cycle_status.json`
- `truth_cycle_status.md`

見るもの:

- `cycle_status`
- `human_summary`
- `recommended_next_command`
- `next_steps`
- `stage_checklist`
- `stop_reasons`
- `known_gaps`
- `operator_decision`
- 各stageの `present` / `status`

`next_steps` は `recommended_next_command` より先に読みます。`verify_artifact_path` が出ている場合は、CLIを再実行する前に指定pathやrun directoryを確認します。`requires_explicit_approval=true` が出ている場合は、このrunbookから先へは進めません。

`stage_checklist` は各stageの入力表です。`blocks_progress=true` のstageを先に見ます。`expected_cli_option` は `crypto-perp-truth-cycle-status` に渡すoption名、`expected_artifact_hint` はそのstageで必要なartifact種別です。`stage_checklist` の blocker を残したまま、次のstageの勝ち筋やtiny live判断へ進めません。

`status=path_not_found` は、指定したartifact pathが存在しないという意味です。`MISSING_PROBE_AUDIT` などの通常欠損と混同せず、path typo / 未生成 / 別run directoryを先に確認します。tournament gateが `NEEDS_ACTUAL_CASH` などで止まった場合は、gate status と failed condition も `stop_reasons` に出ます。

これは既存artifactを読むだけです。public network、credential、wallet、signing、exchange write、live orderは使いません。

既存の rows JSON / JSONL がある場合、まずtournament reportだけを再生成します。

```bash
uv run sis crypto-perp-tournament-report \
  --rows data/crypto_perp/tournament/rows.jsonl \
  --out data/crypto_perp/tournament/latest \
  --report-id crypto-perp-tournament-latest \
  --min-events 10
```

見るもの:

- `tournament_status`
- `leader_action`
- `primary_metric=actual_cash_result_usd`
- `event_count`
- `inconclusive_reasons`
- 各actionの `largest_loss_usd`
- `profit_concentration`
- `operator_time_minutes`

止める条件:

- `tournament_status=INCONCLUSIVE_DATA`
- event set が action 間で一致しない
- `NO_TRADE` を失敗扱いしている
- `REVERSAL_SHORT` だけを勝ち前提にしている
- actual cash ではなく勝率だけで判断している

## P01: candidate event からprospective decisionを記録する

event cardを先に読みます。

```bash
uv run sis crypto-perp-watchdeck \
  --event data/crypto_perp/events/<event-id>/event.json
```

outcome を見る前に decision を記録します。

```bash
uv run sis crypto-perp-decision-record \
  --event data/crypto_perp/events/<event-id>/event.json \
  --action NO_TRADE \
  --out data/crypto_perp/decisions/<event-id> \
  --actor-type human \
  --actor-id operator \
  --size-cap-usd 0 \
  --reason-code insufficient_evidence \
  --notes "prospective decision before outcome"
```

action候補:

- `REVERSAL_SHORT`
- `CONTINUATION_LONG`
- `NO_TRADE`
- `UNKNOWN`
- `CAPTURE_ONLY`

注意:

- `decision_at` は `information_cutoff_at` 以後でなければならない。
- decision artifact は outcome / pnl を含まない。
- `size_cap_usd` は上限記録であり、order permissionではない。
- `UNKNOWN` や `NO_TRADE` は失敗ではなく、証拠不足や見送りを明示するための選択肢。

## P02: public probe後にevent候補へ進めるか検査する

public network probeは明示的な人間承認と環境変数opt-inがある時だけ実行します。

```bash
SIS_ALLOW_PUBLIC_NETWORK=1 uv run sis crypto-perp-probe \
  --config configs/crypto_perp/bitget_personal_edge_lab.yaml \
  --out data/crypto_perp/provider_probe/latest \
  --raw-root data/crypto_perp/raw \
  --network
```

probe後は、event候補へ進める前にauditします。

```bash
uv run sis crypto-perp-probe-audit \
  --probe data/crypto_perp/provider_probe/latest/provider_probe.json \
  --out data/crypto_perp/probe_audit/latest
```

見るもの:

- `audit_status`
- `missing_endpoints`
- `zero_row_endpoints`
- `failed_endpoints`
- `missing_capabilities`
- `missing_raw_snapshot_paths`
- `known_gaps`
- `next_actions`

進める条件:

- `audit_status=READY_FOR_EVENT_REFRESH`
- `network_attempted=true` のprobe artifactである
- `credentials_used=false`
- `instruments`、`tickers`、`candles` が存在し、row_countが0ではない
- raw snapshot pathが存在する

止める条件:

- `audit_status=BLOCKED_PROBE_QUALITY`
- raw snapshotが欠けている
- tickers / candles が0行
- endpoint errorがある
- credentialsを使ったartifactが混ざっている
- auditを通さずevent候補を増やす

## P03: audit済みraw snapshotからsnapshot / event候補を再生成する

`crypto-perp-probe-audit` が `READY_FOR_EVENT_REFRESH` の時だけ実行します。

```bash
uv run sis crypto-perp-raw-refresh \
  --probe data/crypto_perp/provider_probe/latest/provider_probe.json \
  --probe-audit data/crypto_perp/probe_audit/latest/probe_audit.json \
  --out data/crypto_perp/raw_refresh/latest
```

生成物:

- `raw_refresh.json`
- `raw_refresh.md`
- `universe_snapshot.json`
- `market_snapshot.json`
- `candle_quality.json`
- `events/<event-id>.json`。eventが無い場合は0件として残す。

見るもの:

- `event_count`
- `known_gaps`
- `universe_instrument_count`
- `market_ticker_count`
- `candle_bar_count`

止める条件:

- probe audit が `READY_FOR_EVENT_REFRESH` ではない
- `probe_id` が probe と audit で一致しない
- raw snapshot が欠けている
- candle qualityに `GAP_DETECTED` / `NON_FINAL_BAR` / `INVALID_OHLC` がある
- `NO_EVENT_DETECTED` を無理にevent化する

## P04: matured outcomeを記録する

観察窓が成熟したあとで outcome を記録します。

```bash
uv run sis crypto-perp-outcome-record \
  --event data/crypto_perp/events/<event-id>/event.json \
  --out data/crypto_perp/outcomes/<event-id> \
  --horizon-minutes 60 \
  --reference-price 100 \
  --close-price 105 \
  --high-price 110 \
  --low-price 95 \
  --market-return 0
```

高解像度の順序証拠がある場合だけ、次を追加します。

```bash
--observed-high-low-order HIGH_FIRST
```

順序が分からない場合は指定しません。その場合、OHLC内の high / low 順序は `AMBIGUOUS` として残します。

止める条件:

- horizonが未成熟なのに `--matured` として記録する
- high / low の順序を証拠なしに決める
- books / trades の欠落を `--known-gap` に残さない
- outcomeをdecision前に見てdecisionを作る

## P05: tournament rowsを作る

outcome artifactから、tournament reportへ渡す3action rowsのpreviewを作れます。

```bash
uv run sis crypto-perp-tournament-rows-preview \
  --outcome data/crypto_perp/outcomes/<event-id>/<outcome-id>.json \
  --out data/crypto_perp/tournament_rows_preview/<event-id> \
  --notional-usd 25 \
  --operator-time-minutes 2
```

生成物:

- `tournament_rows_preview.json`
- `tournament_rows.jsonl`
- `tournament_rows_preview.md`

注意:

- これは `outcome_before_cost_proxy` です。実約定、fee、funding、slippage込みのactual cashではありません。
- preview rows の各 row は `cash_metric_basis=before_cost_proxy` と `cash_metric_value_usd` を持ち、`actual_cash_result_usd` は `null` です。
- `OUTCOME_BEFORE_COST_PROXY_NOT_ACTUAL_CASH` と `FEES_FUNDING_AND_FILL_SLIPPAGE_NOT_INCLUDED` をknown gapとして残します。
- `NO_TRADE` はcash 0として明示します。失敗扱いしません。
- `tournament_rows_preview.json` は display / dogfood 用です。`crypto-perp-tournament-report --rows` へ渡すと `PREVIEW_ROWS_NOT_ACTUAL_CASH` で失敗します。
- outcome 由来の estimate / cost-aware 比較は `crypto-perp-tournament-rows-v2` を使います。

手で作る場合も、winnerだけを保存しません。各eventについて、同じevent setで次の3actionをそろえます。

```json
{"event_id":"event-1","action":"REVERSAL_SHORT","cash_metric_value_usd":"-1.20","actual_cash_result_usd":"-1.20","cash_metric_basis":"actual_cash","market_adjusted_return":"-0.02","operator_time_minutes":"3","near_miss":false}
{"event_id":"event-1","action":"CONTINUATION_LONG","cash_metric_value_usd":"0.80","actual_cash_result_usd":"0.80","cash_metric_basis":"actual_cash","market_adjusted_return":"0.01","operator_time_minutes":"3","near_miss":false}
{"event_id":"event-1","action":"NO_TRADE","cash_metric_value_usd":"0","actual_cash_result_usd":"0","cash_metric_basis":"actual_cash","market_adjusted_return":"0","operator_time_minutes":"0","near_miss":false}
```

入力制約:

- 1 event につき `REVERSAL_SHORT`、`CONTINUATION_LONG`、`NO_TRADE` を1行ずつ入れる。
- `cash_metric_basis=actual_cash` を明示する。未指定時は互換のため actual cash と解釈されるが、手作業JSONLでは省略しない。
- `cash_metric_value_usd` を正の比較値として入れる。
- `actual_cash_result_usd` は actual cash basis の時だけ同じ値を入れる legacy alias。旧JSONL互換のため、`cash_metric_value_usd` が無いactual cash rowは読み取り時に `actual_cash_result_usd` から補完される。
- fee、funding、ruined pod、infra costがある場合はcash側に含める。
- データ不足は行を消して隠すのではなく、reportの `INCONCLUSIVE_DATA` または `known_gaps` に残す。
- before-cost proxy rowsを実cashとして扱わない。

## P06: reportから次 action を決める

PR-I2 local automation は、実 event / matured outcome / actual cash ledger が無い状態を成功扱いにしません。dogfood/status/viewer は profit evidence ではありません。まず inventory / plan で、ローカルに進められるかを確認します。

```bash
uv run sis crypto-perp-profit-readiness-inventory \
  --data-dir data/crypto_perp \
  --out data/crypto_perp/artifact_inventory/latest

uv run sis crypto-perp-profit-readiness-plan \
  --inventory data/crypto_perp/artifact_inventory/latest/inventory.json \
  --out data/crypto_perp/profit_readiness_plan/latest
```

止まる条件:

- `inventory_status=BLOCKED_MISSING_EVENT_OR_OUTCOME`: real event または matured outcome が無い。
- `plan_status=BLOCKED_MULTIPLE_EVENT_OR_OUTCOME_CANDIDATES`: 複数候補があり、自動選択しない。

event/outcome が1件ずつに絞れている場合だけ、plan の command chain または次の local runner を使います。

```bash
uv run sis crypto-perp-profit-readiness-run-local \
  --event data/crypto_perp/events/<event-id>/event.json \
  --outcome data/crypto_perp/outcomes/<event-id>/<outcome-id>.json \
  --notional-usd 25 \
  --out data/crypto_perp/profit_readiness_run/<event-id>
```

actual cash tournament rows は cash ledger と assignment からだけ作ります。preview / estimate / dogfood artifact から actual cash rows を作りません。

```bash
uv run sis crypto-perp-cash-ledger \
  --entries data/crypto_perp/cash/entries.jsonl \
  --ledger-id <ledger-id> \
  --observed-at 2026-06-21T07:00:00Z \
  --out data/crypto_perp/cash_ledger/<ledger-id>

uv run sis crypto-perp-actual-cash-rows-build \
  --ledger data/crypto_perp/cash_ledger/<ledger-id>/cash_ledger.json \
  --assignment data/crypto_perp/cash/assignment.json \
  --out data/crypto_perp/tournament/<report-id>/actual_cash_rows
```

assignment は `event_id`、`action`、`pod_id` を明示します。`NO_TRADE` は `pod_id=null` と cash 0 を許可します。`REVERSAL_SHORT` / `CONTINUATION_LONG` は ledger entry が無ければ失敗し、0埋めしません。

actual-cash report / gate / review packet / readiness は次の順で進めます。ready になっても live order permission ではなく、明示承認待ちの資料です。

```bash
uv run sis crypto-perp-actual-cash-report-gate \
  --rows data/crypto_perp/tournament/<report-id>/actual_cash_rows/actual_cash_rows.jsonl \
  --report-id <report-id> \
  --min-events 10 \
  --out data/crypto_perp/tournament/<report-id>/report_gate

uv run sis crypto-perp-tiny-live-review-packet \
  --report data/crypto_perp/tournament/<report-id>/report_gate/tournament_report.json \
  --gate data/crypto_perp/tournament/<report-id>/report_gate/tournament_gate.json \
  --out data/crypto_perp/tiny_live_review_packet/<report-id>

uv run sis crypto-perp-tiny-live-shadow-readiness \
  --packet data/crypto_perp/tiny_live_review_packet/<report-id>/review_packet.json \
  --account data/crypto_perp/account/<snapshot-id>/account_snapshot.json \
  --order-preview data/crypto_perp/order_preview/<preview-id>/order_preview.json \
  --out data/crypto_perp/tiny_live_shadow_readiness/<report-id>
```

`crypto-perp-tiny-live-shadow-readiness` は shadow 実行や real measurement をしません。出力は `live_order_allowed=false`、`exchange_write_allowed=false`、`requires_explicit_approval=true` 固定です。

profit-readiness 層で source availability、replay slice、feature pack、edge score、cost-aware rows、bias guardを作る場合は、次の順で local artifact を作ります。

```bash
uv run sis crypto-perp-source-availability \
  --event data/crypto_perp/events/<event-id>/event.json \
  --available-source bars \
  --available-source ticker \
  --available-source funding \
  --row-count bars=592 \
  --out data/crypto_perp/source_availability/<event-id>

uv run sis crypto-perp-replay-slice \
  --event data/crypto_perp/events/<event-id>/event.json \
  --included-source event \
  --included-source bars \
  --row-count bars=592 \
  --out data/crypto_perp/replay_slice/<event-id>

uv run sis crypto-perp-feature-pack \
  --event data/crypto_perp/events/<event-id>/event.json \
  --source-availability data/crypto_perp/source_availability/<event-id>/source_availability.json \
  --out data/crypto_perp/feature_pack/<event-id>

uv run sis crypto-perp-edge-score \
  --feature-pack data/crypto_perp/feature_pack/<event-id>/feature_pack.json \
  --source-availability data/crypto_perp/source_availability/<event-id>/source_availability.json \
  --out data/crypto_perp/edge_score/<event-id>

uv run sis crypto-perp-tournament-rows-v2 \
  --outcome data/crypto_perp/outcomes/<event-id>/<outcome-id>.json \
  --notional-usd 25 \
  --fee-rate 0.0004 \
  --funding-rate 0.0001 \
  --slippage-bps 2 \
  --operator-time-minutes 2 \
  --operator-hourly-cost-usd 60 \
  --out data/crypto_perp/tournament_rows_v2/<event-id>

uv run sis crypto-perp-bias-guard \
  --rows-v2 data/crypto_perp/tournament_rows_v2/<event-id>/tournament_rows_v2.json \
  --min-events-for-pbo 30 \
  --fold-count 0 \
  --out data/crypto_perp/bias_guard/<event-id>
```

見るもの:

- `source_availability.can_compute_*`
- `feature_pack.known_gaps`
- `edge_score.selected_action` と `why_no_trade`
- `tournament_rows_v2.rows[].cost_adjusted_cash_estimate_usd`
- `tournament_rows_v2.rows[].stress_cash_estimate_usd`
- `tournament_rows_v2.rows[].evidence_level`
- `bias_guard.guard_status`
- `bias_guard.pbo_status`
- `bias_guard.stop_reasons`

`crypto-perp-tournament-rows-v2` の normal project assumption は `fee_rate=0.0004`、`funding_rate=0.0001`、`slippage_bps=2` です。stress は `stress_cash_estimate_usd` と explicit stress multiplier で読み、actual cash や measured exchange cost と混同しません。

`crypto-perp-tournament-rows-v2` は estimate surface です。`actual_cash_result_usd` は actual cash evidence が渡された場合だけ使い、通常の outcome 由来 rows では `null` のまま読みます。比較値は basis に応じた `cash_metric_value_usd` / estimate field で読みます。

`crypto-perp-tournament-report` に渡せるのは、caller が actual cash 責任を持つ `TournamentEventResult` JSON / JSONL です。preview rows、`OUTCOME_BEFORE_COST_PROXY_NOT_ACTUAL_CASH` を持つ rows、または `cash_metric_basis != actual_cash` の rows は report input として使えません。

```bash
uv run sis crypto-perp-tournament-report \
  --rows data/crypto_perp/tournament/actual_cash_rows.jsonl \
  --out data/crypto_perp/tournament/<report-id> \
  --report-id <report-id> \
  --min-events 10 \
  --known-gap books15_missing
```

進める条件:

- `tournament_status=COMPLETE`
- event set が3actionで一致している
- `cash_metric_basis=actual_cash`
- `actual_cash=true`
- `primary_metric_display_name=actual_cash_result_usd`
- `OUTCOME_BEFORE_COST_PROXY_NOT_ACTUAL_CASH` が残っているrowsをreport inputとして扱っていない
- largest loss が許容範囲
- profit concentration が極端ではない
- operator time が継続可能

戻す条件:

- `INCONCLUSIVE_DATA`
- leaderが出ない
- 1 event へのprofit集中が強すぎる
- `NO_TRADE` がactual cash basisで最良
- fill / fee / funding / cash attributionが不明
- high / low ordering ambiguity がdecisionを左右している

次に、reportをgateに通します。

```bash
uv run sis crypto-perp-tournament-gate \
  --report data/crypto_perp/tournament/<report-id>/tournament_report.json \
  --out data/crypto_perp/tournament_gate/<report-id> \
  --max-largest-loss-usd 25 \
  --max-profit-concentration 0.60 \
  --max-operator-time-minutes 120
```

見るもの:

- stdoutの `status`
- `gate_status`
- `recommended_action`
- `requires_explicit_approval`
- `permits_live_order`
- `failed_conditions`
- `known_gaps`

`READY_FOR_HUMAN_TINY_LIVE_REVIEW` の時、CLI stdout は `status=needs_human_approval`、`requires_explicit_approval=true`、`permits_live_order=false` として読みます。これは承認準備の入口であり、live実行許可ではありません。`status=needs_human_approval` を `status=pass` と読み替えないでください。

## tiny live measurementへ進む前の境界

tiny live measurement はこのrunbookの範囲外です。進むには別の明示承認が必要です。

承認前の非発注 preflight だけを shadow artifact にする場合は、次を使います。

```bash
uv run sis crypto-perp-tiny-live-shadow \
  --account data/crypto_perp/account_probe/latest/account_snapshot.json \
  --order-preview data/crypto_perp/order_preview/latest/order_preview.json \
  --out data/crypto_perp/tiny_live_shadow/latest \
  --max-notional-usd 25
```

この artifact は `exchange_write_used=false`、`live_order_submitted=false`、`permits_live_order=false` を必ず満たします。`preflight_status=PASS` でも実発注許可ではありません。

最低条件:

- `SIS_ENABLE_TINY_LIVE_MEASUREMENT=1`
- `--confirm-live`
- confirmation phrase
- isolated margin
- withdrawal disabled API key
- IP restriction
- max notional 25 USD
- max open positions 1
- no existing position
- no existing open order
- reduce-only close
- flat reconciliation

## 検証

このrunbookや関連CLIを変更した時は次を実行します。

```bash
uv run pytest tests/crypto_perp/test_provider_probe.py tests/crypto_perp/test_raw_refresh.py tests/crypto_perp/test_decisions.py tests/crypto_perp/test_outcomes.py tests/crypto_perp/test_tournament_rows.py tests/crypto_perp/test_tournament.py tests/crypto_perp/test_tournament_gate.py -q
uv run pytest tests/crypto_perp/test_truth_cycle_status.py -q
uv run python scripts/check_cli_catalog.py
uv run python scripts/check_current_docs.py
./scripts/check
```
