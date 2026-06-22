<!--
作成日: 2026-06-17_10:00 JST
更新日: 2026-06-22_14:47 JST
-->

# Next Direction Current

## 結論

現時点の現実的な方向は、backtest-first / venue-neutral を維持しながら、実装済みの Strategy Input Contract / Idea Intake first gate、Strategy Review の人間判断記録、Strategy Stage Policy / Decision first slice、Strategy Paper Smoke Plan first slice、Strategy Runtime Observation Ingest first slice、Paper vs Backtest Drift Review first slice、Strategy Learning / Revision Request first slice、Strategy Case Lite first slice、Strategy Daily Brief first slice、Strategy AI Review first slice、Strategy Model Loop first slice、Strategy Micro Live Plan Gate first slice、Strategy Next Scale Plan first slice、Strategy Live Observation first slice、Strategy Scale Decision first slice、Strategy Workbench Viewer first slice、paper observation の通常threshold状態を次段検証の土台にすることです。

これは確定ロードマップではありません。実装済み surface と未実装候補を混ぜず、次に狙いやすい方向、追加候補、優先しないことを分けるための current doc です。

完成形の設計定義は [TARGET_STRATEGY_OPERATIONS_WORKBENCH_2026-06-18.md](TARGET_STRATEGY_OPERATIONS_WORKBENCH_2026-06-18.md) を読む。これは current implementation proof ではなく、個人システムトレーダー向けに stage policy、paper smoke、drift review、micro live plan gate をどう位置づけるかの target definition です。

完成形を実装完了まで閉じるために使った作業順、対象ファイル、テスト方針、完了条件は [archive/2026-06-22-doc-routing/STRATEGY_OPERATIONS_WORKBENCH_COMPLETION_PLAN_2026-06-19.md](archive/2026-06-22-doc-routing/STRATEGY_OPERATIONS_WORKBENCH_COMPLETION_PLAN_2026-06-19.md) に historical plan として移動済みです。現行利用では `IMPLEMENTED_SURFACES.md` と各 domain README を先に読みます。

T0〜T12b の実装証跡と残る対象外範囲は [archive/2026-06-22-doc-routing/STRATEGY_OPERATIONS_WORKBENCH_COMPLETION_AUDIT_2026-06-19.md](archive/2026-06-22-doc-routing/STRATEGY_OPERATIONS_WORKBENCH_COMPLETION_AUDIT_2026-06-19.md) に historical audit として残します。

Crypto Perp の実装済み handoff は [../plan/archive/2026-06-22-crypto-perp-mvp-implemented/marketlens-strike-crypto-perp-mvp-final-plan-2026-06-20/00_READ_ME_FIRST.md](../plan/archive/2026-06-22-crypto-perp-mvp-implemented/marketlens-strike-crypto-perp-mvp-final-plan-2026-06-20/00_READ_ME_FIRST.md) に historical implementation contract として残します。現行の入口は下の post-MVP practical loop と [runbooks/CRYPTO_PERP_TRUTH_CYCLE_RUNBOOK.md](runbooks/CRYPTO_PERP_TRUTH_CYCLE_RUNBOOK.md) です。M09 の実ネットワーク 5〜25 USD 測定は別の明示承認がある時だけ扱います。

実装順、対象ファイル、acceptance の履歴は [../plan/archive/2026-06-22-crypto-perp-mvp-implemented/marketlens-strike-crypto-perp-mvp-final-plan-2026-06-20/07_TASK_CHAIN.yaml](../plan/archive/2026-06-22-crypto-perp-mvp-implemented/marketlens-strike-crypto-perp-mvp-final-plan-2026-06-20/07_TASK_CHAIN.yaml) を読む。M00 の current truth alignment と supersession、M01 の domain foundation / config / fail-closed CLI boundary / Hypothesis、M02 の Bitget public probe / immutable raw snapshots、M03 の universe diff / ticker snapshot / broad 15m history foundation、M04 の event capture and event card MVP-A、M05 の candidate-only high-resolution recorder、M06 の prospective decision and outcome ledger MVP-B、M07 の validation accelerator pack、M08 の credentialed read-only and order preview、M09 の tiny live execution calibration MVP-C、M10 の actual cash ledger and replay calibration、M11 の hypothesis tournament and Workbench bridge は実装済みです。M09 の実ネットワーク 5〜25 USD 測定は別の明示承認がある時だけ扱います。

## Crypto Perp Post-MVP Practical Loop

利益目的に向けた次の現実的なループは、勝ち筋を先に決めることではなく、同じevent setで `REVERSAL_SHORT`、`CONTINUATION_LONG`、`NO_TRADE` をactual cash basisで比較し、データ不足を `INCONCLUSIVE_DATA` として残すことです。

実装済みの次入口:

- `crypto-perp-truth-cycle-status`: 手元のprobe audit / raw refresh / event / decision / outcome / rows / report / gate artifactを読み、次に欠けているlocal step、stop reason、known gapsを出す。network / order / live permissionではない。
- `crypto-perp-decision-record`: event JSONから outcome前の `crypto_perp_decision.v1` を作る。
- `crypto-perp-outcome-record`: event JSONまたはevent idから `crypto_perp_outcome.v1` を作る。
- `crypto-perp-probe-audit`: public provider probe後に、event候補へ進めるだけのendpoint / raw snapshot証拠があるかをlocal artifactで判定する。
- `crypto-perp-raw-refresh`: audit済みprobe rawから universe snapshot、market snapshot、candle quality、event候補をlocal artifactとして再生成する。
- `crypto-perp-tournament-rows-preview`: matured outcomeから `REVERSAL_SHORT`、`CONTINUATION_LONG`、`NO_TRADE` の3action rows previewを作る。これは before-cost proxy であり、actual cash実績ではない。
- `crypto-perp-tournament-report`: JSON / JSONL rowsから `crypto_perp_tournament_report.v1` とMarkdown reportを作る。
- `crypto-perp-tournament-gate`: reportから proxy gap、event不足、NO_TRADE leader、largest loss、profit concentration、operator time を読んで、次actionをlocal artifactに分ける。live order permissionではない。
- [runbooks/CRYPTO_PERP_TRUTH_CYCLE_RUNBOOK.md](runbooks/CRYPTO_PERP_TRUTH_CYCLE_RUNBOOK.md): candidate eventからdecision / outcome / tournament reportまでの再生成手順。

次に進める順番:

1. P00: fixture / historical rowsでtournament reportを再生成し、leaderが出ない時に無理に進めない。
2. P01: candidate eventからdecision / outcome / tournament rows previewまでの生成手順をrunbook化する。before-cost proxy rowsをactual cashとして扱わない。現行runbookは [runbooks/CRYPTO_PERP_TRUTH_CYCLE_RUNBOOK.md](runbooks/CRYPTO_PERP_TRUTH_CYCLE_RUNBOOK.md)。
3. P02: public-network opt-inありのBitget public probeを人間実行し、`crypto-perp-probe-audit` が `READY_FOR_EVENT_REFRESH` の時だけraw snapshotを使う。
4. P03: `crypto-perp-raw-refresh` でaudit済みraw snapshotからuniverse / market / event候補を再生成し、event 0件やquality gapもそのまま残す。
5. P04: proxy rowsや十分なevent数がそろっても `INCONCLUSIVE_DATA` なら、thresholdやevent definitionをlearning / revision requestへ戻す。
6. P05: `crypto-perp-tournament-gate` が `READY_FOR_HUMAN_TINY_LIVE_REVIEW` の時だけ、tiny live measurementの承認準備に進む。これは実行許可ではなく、人間が承認条件を確認する入口です。

やらないこと:

- `REVERSAL_SHORT` を勝ち前提にする。
- `NO_TRADE` を失敗扱いにする。
- backtestやfixtureだけで利益があると断定する。
- M09のmock testを実ネットワーク測定済みとして扱う。
- tiny live承認なしにcredentialed write、注文、daemon、自動売買へ進む。

Strategy Input Contract / Idea Intake first gate と Strategy Review optional source connection の設計履歴は [archive/2026-06-22-doc-routing/STRATEGY_INPUT_CONTRACT_AND_IDEA_INTAKE_IMPLEMENTATION_PLAN_2026-06-18.md](archive/2026-06-22-doc-routing/STRATEGY_INPUT_CONTRACT_AND_IDEA_INTAKE_IMPLEMENTATION_PLAN_2026-06-18.md) を読む。これは実装済み slice の historical coder handoff です。現行の使い方は [strategy_inputs/README.md](strategy_inputs/README.md) を読む。

Strategy Stage Policy / Decision の使い方は [strategy_stage/README.md](strategy_stage/README.md) を読む。これは `strategy_stage_policy.v1`、`strategy_stage_policy_validation.v1`、`strategy_stage_decision.v1`、`strategy-stage-policy-validate`、`strategy-stage-decision` の current surface です。

Strategy Paper Smoke Plan の使い方は [strategy_paper_smoke/README.md](strategy_paper_smoke/README.md) を読む。これは `strategy_paper_smoke_plan.v1` と `strategy-paper-smoke-plan` の current surface です。

Strategy Runtime Observation の使い方は [strategy_runtime_observation/README.md](strategy_runtime_observation/README.md) を読む。これは `strategy_runtime_observation_manifest.v1` と `strategy-runtime-observation-ingest` の current surface です。

Paper vs Backtest Drift Review の使い方は [strategy_drift_review/README.md](strategy_drift_review/README.md) を読む。これは `paper_vs_backtest_drift_review.v1` と `strategy-drift-review` の current surface です。

Strategy Learning の使い方は [strategy_learning/README.md](strategy_learning/README.md) を読む。これは `strategy_learning_event.v1`、`strategy_revision_request.v1`、`strategy_revision_request_review.v1`、`strategy_authoring_update_handoff.v1`、`strategy-learning-ledger-update`、`strategy-revision-request-build`、`strategy-revision-request-review`、`strategy-authoring-update-handoff` の current surface です。

Strategy Case Lite の使い方は [strategy_case_lite/README.md](strategy_case_lite/README.md) を読む。これは `strategy_case_lite.v1` と `strategy-case-lite-update` の current surface です。

Strategy Daily Brief の使い方は [strategy_daily_brief/README.md](strategy_daily_brief/README.md) を読む。これは `strategy_daily_brief.v1` と `strategy-daily-brief` の current surface です。

Strategy AI Review の使い方は [strategy_ai_review/README.md](strategy_ai_review/README.md) を読む。これは `strategy_ai_review_packet.v1`、`strategy_ai_review_note.v1`、`strategy-ai-review-packet-build`、`strategy-ai-review-note-record` の current surface です。

Strategy Model / Optimizer Loop の使い方は [strategy_model_loop/README.md](strategy_model_loop/README.md) を読む。これは `strategy_model_run.v1`、`strategy_optimizer_trial_ledger.v1`、`strategy-model-run-record` の current surface です。

Strategy Micro Live Plan Gate の使い方は [strategy_micro_live_plan/README.md](strategy_micro_live_plan/README.md) を読む。これは `strategy_micro_live_plan.v1` と `strategy-micro-live-plan` の current surface です。

Strategy Next Scale Plan の使い方は [strategy_next_scale_plan/README.md](strategy_next_scale_plan/README.md) を読む。これは `strategy_next_scale_plan.v1` と `strategy-next-scale-plan` の current surface です。

Strategy Live Observation の使い方は [strategy_live_observation/README.md](strategy_live_observation/README.md) を読む。これは `strategy_live_observation_manifest.v1` と `strategy-live-observation-ingest` の current surface です。

Strategy Scale Decision の使い方は [strategy_scale_decision/README.md](strategy_scale_decision/README.md) を読む。これは `strategy_scale_decision.v1` と `strategy-scale-decision` の current surface です。

Strategy Workbench Viewer の使い方は [strategy_workbench_viewer/README.md](strategy_workbench_viewer/README.md) を読む。これは `strategy_workbench_viewer.v1` と `strategy-workbench-viewer-build` の current surface です。

## 正本

この文書は次を正本として読む:

- code: `src/`, `tests/`, `configs/`, `schemas/`, `scripts/`
- CLI help: `uv run sis --help`, `uv run sis strategy-review-record --help`
- current docs: `docs/CURRENT_STATE.md`, `docs/IMPLEMENTED_SURFACES.md`, `docs/REPO_CAPABILITIES_CURRENT_2026-06-16.md`, `docs/strategy_review/README.md`

次は current proof として扱わない:

- stale plan
- historical audit
- archived plan handoff
- archived implementation-sequence snapshot: `docs/archive/2026-06-17-doc-routing/NEXT_IMPLEMENTATION_SEQUENCE_CURRENT.md`
- `data/` runtime artifact
- old pass count / public command count snapshot

## Near-Term Practical Direction

1. Backtest-first / venue-neutral を継続する。
2. Strategy Review の `strategy-review-build` / `strategy-review-record` を、既存 artifact を人間が読み、判断記録を残すための土台として使う。
3. `PAPER_OBSERVATION_CANDIDATE` は validation candidate としてのみ扱い、paper 実行許可や paper intent 生成許可とは読まない。
4. paper observation は normal threshold と smoke threshold を分けて読む。smoke pass は normal paper observation pass ではない。
5. future venue は `venue-read-only-probe` dogfood 済みで、現時点では `NO_ACTION`。schema や paper path は広げない。

## Implemented First Gate

### Strategy Input Contract / Idea Intake

通常 paper の追加実行より先に必要だった Strategy Input Contract / Idea Intake first gate は実装済みです。

できること:

- 入力データを path / hash だけでなく、`available_at`、revision policy、survivorship policy、execution reality 付きで契約化する。
- 戦略の種を hypothesis、baseline、invalidation、risk、required inputs 付きで記録する。
- `strategy-input-contract-validate` で source path、sha256、missing required、boundary violation、required columns、timestamp upper bound、available_at column を検査する。
- `strategy-intake-validate` で `READY_FOR_AUTHORING_DRAFT` / `NEEDS_SPEC` / `NEEDS_DATA_CHECK` / `NEEDS_RISK_SPEC` / `REJECT` を local artifact として出す。
- `strategy-review-build --input-contract --strategy-idea` で input contract と strategy idea を review packet の optional source artifact として読む。

残 task:

- Runtime Observation を Strategy Input Contract へ自動反映する処理は未実装。

対象外:

- Paper Smoke execution automation
- AI / ML / GA
- UI
- wallet / signing / exchange write
- live execution

### Strategy Stage Policy / Decision

Stage Policy / Decision first slice は実装済みです。

できること:

- `strategy_stage_policy.v1` で、`paper_smoke`、`normal_paper_observation`、`drift_review`、`micro_live_plan` の条件を config 化する。
- `strategy-stage-policy-validate` で、fixed safety、stage completeness、rate range、no-live boundary を検査する。
- `strategy-stage-decision` で、operator review または paper observation status を読み、次 stage の計画に進める証拠があるかを local artifact にする。
- decision に policy hash、source artifact hash、passed / failed condition、manual override reason を残す。

実務上の注意:

- `READY_FOR_PAPER_SMOKE_PLAN` は paper order 実行許可ではない。
- `READY_FOR_MICRO_LIVE_PLAN` は micro live execution permission ではない。
- manual override は記録されるだけで、failed evidence を自動合格にしない。

### Strategy Paper Smoke Plan

Paper Smoke Plan first slice は実装済みです。

できること:

- `strategy-paper-smoke-plan` で、`READY_FOR_PAPER_SMOKE_PLAN` の stage decision から `strategy_paper_smoke_plan.v1` JSON と Markdown report を作る。
- Stage Policy の `paper_smoke` threshold を読み、`strategy-paper-observation-cycle --smoke` の実行 preview に反映する。
- backtest acceptance、paper candidate pack、promotion decision、operator promotion の source artifact 存在と hash を記録する。
- source artifact が足りない場合は `NEEDS_SOURCE_ARTIFACTS` として、欠落を plan artifact に残す。

残 task:

- Svelte UI は未実装。現行 repo では static viewer `strategy-workbench-viewer-build` を使う。

実務上の注意:

- `READY_TO_RUN_SMOKE_CYCLE` は paper smoke cycle の実行計画であり、自動 paper 実行ではない。
- smoke pass は normal paper observation pass ではない。
- 実際の smoke 実行は人間が execution preview を読み、明示的に `strategy-paper-observation-cycle --smoke` を実行する。

### Strategy Runtime Observation Ingest

Runtime Observation Ingest first slice は実装済みです。

できること:

- `strategy-runtime-observation-ingest` で、paper observation session manifest と observation ledger を読み、`strategy_runtime_observation_manifest.v1` JSON と Markdown summary を作る。
- `runtime_observation_ledger.jsonl` として paper runtime ledger を正規化コピーする。
- fills、blocked、no-fill、spread、quote age、block reason を summary にする。
- live / wallet / signing / exchange write 系の true flag が混入したら `BLOCKED_BOUNDARY_VIOLATION` にする。

残 task:

- Runtime observation を Strategy Input Contract へ自動反映する処理は未実装。

実務上の注意:

- この ingest は paper runtime artifact を読むだけで、paper order も live order も出さない。
- `INGESTED` は paper pass や live readiness ではない。

### Paper vs Backtest Drift Review

Paper vs Backtest Drift Review first slice は実装済みです。

できること:

- `strategy-drift-review` で、`strategy_authoring_backtest_result.v1` と `strategy_runtime_observation_manifest.v1` を読み、`paper_vs_backtest_drift_review.v1` JSON と Markdown report を作る。
- backtest の `trade_count`、`total_return`、`max_drawdown`、`backtest_passed` と、paper runtime の fills、blocked、no-fill、spread、quote age を並べる。
- `--max-no-fill-rate`、`--max-blocked-rate`、`--max-spread-bps` によって `recommended_action` を `HUMAN_REVIEW_REQUIRED`、`EXTEND_OBSERVATION`、`REVISE_STRATEGY`、`REPAIR_ARTIFACTS` に分ける。
- live / wallet / signing / exchange write 系 true flag が混入したら `BLOCKED_BOUNDARY_VIOLATION` にする。

次の読み口:

- `strategy-workbench-viewer-build` で Drift Review と関連 artifact を static HTML viewer にまとめられる。

実務上の注意:

- `READY_FOR_HUMAN_DRIFT_REVIEW` は micro live plan の許可ではない。
- `HUMAN_REVIEW_REQUIRED` は人間が読む必要があるという意味であり、合格ではない。
- no-fill、blocked、spread の悪化が見えた場合は、進めるのではなく Strategy Idea / Authoring spec / execution assumption へ戻す。

### Strategy Learning / Revision Request / Authoring Update Handoff

Strategy Learning / Revision Request / Authoring Update Handoff first slice は実装済みです。

できること:

- `strategy-learning-ledger-update` で、`paper_vs_backtest_drift_review.v1` から `strategy_learning_event.v1` を作り、`learning_ledger.jsonl` と `learning_summary.md` に反映する。
- `strategy-revision-request-build` で、learning ledger から `strategy_revision_request.v1` JSON と Markdown report を作る。
- `strategy-revision-request-review` で、revision request に対する人間判断を `strategy_revision_request_review.v1` JSON と Markdown report に記録する。
- `strategy-authoring-update-handoff` で、`APPROVE_FOR_AUTHORING_UPDATE` 済み review と現行 Strategy Authoring YAML を source hash 付きで結び、次の人間編集タスクを `strategy_authoring_update_handoff.v1` JSON と Markdown report にする。
- `REVISE_STRATEGY`、`EXTEND_OBSERVATION`、`REPAIR_ARTIFACTS`、`HUMAN_REVIEW_REQUIRED` を、人間レビュー前提の learning / revision artifact に変換できる。
- `auto_applied=false`、`direct_spec_edit_allowed=false`、`paper_execution_allowed=false`、`live_allowed=false` を固定する。

残 task:

- Learning Event を Strategy Input Contract へ反映する処理は未実装。
- Learning ledger を Strategy Case registry に束ねる処理は未実装。

実務上の注意:

- revision request は採用済み改訂ではない。
- `APPROVE_FOR_AUTHORING_UPDATE` は authoring update の入力許可であり、YAML 自動編集ではない。
- `strategy-authoring-update-handoff` も YAML を自動編集せず、別工程の人間編集入力だけを作る。
- Strategy Authoring YAML を自動で書き換えない。
- `NO_REVISION_REQUIRED` は live readiness ではない。

### Normal threshold paper observation continuation

新しい通常観察 evidence が来た場合に実行価値がある候補は、通常thresholdの paper observation 継続です。これは次のコード実装候補ではなく、外部 evidence が来た時の運用候補です。Strategy Review dogfood は [archive/2026-06-22-doc-routing/DOGFOOD_REVIEW_2026-06-16.md](archive/2026-06-22-doc-routing/DOGFOOD_REVIEW_2026-06-16.md) に historical snapshot として記録済みで、paper observation status artifact も `strategy-paper-observation-status` として実装済みです。

目的:

- `needs_more_normal_paper_observation` の間は、通常thresholdの observation を続ける。
- `--smoke` の pass を normal pass として扱わない。
- lifecycle の `CONTINUE_PAPER_OBSERVATION` を live readiness と読まない。

実務上の注意:

- ここでいう「継続」は、新しい通常観察の証拠を積むことです。同じ trading day の artifact を rerun しても `10 trading days` の代替証拠にはならない。
- 現在の不足量は固定値としてこの文書に写さず、`strategy-paper-observation-status` の `latest_normal_requirement_gaps.fills` と `latest_normal_requirement_gaps.trading_days` を読む。
- fills が満たされていても trading days が残っている場合、必要なのは同日 fill の水増しではなく、別 trading day を含む通常観察です。
- 既存 session に追記する場合は `strategy-paper-observation-append` を使う。新規 session を切る場合も、`latest_normal_requirement_gaps` が進んだかを `strategy-paper-observation-status` で確認する。

実行候補:

```bash
uv run sis strategy-paper-observation-cycle \
  --data-dir data \
  --artifact-dir data/research/ndx \
  --reports-dir data/reports \
  --session-id <normal-session-id>
```

## Needs A New Explicit Plan

次は、進める前に別の明示計画が必要です。

- paper bridge validation
- Strategy Case registry
- UI
- Crypto Perp 計画外の credentialed Bitget read-only network probe。Crypto Perp Truth-Cycle MVP 内の M08 は、M00〜M07 の後に別 task として扱う。
- credentialed Hyperliquid read-only network probe
- Bitget demo order lifecycle
- production venue schema widening

## External Input Restart Checklist

外部入力が揃った場合だけ、次の順で read-only 再確認する。ここでの再確認は execution readiness の観測であり、paper / live 許可ではない。

### Trade[XYZ] read-only execution state

必要な入力:

- `SIS_TRADE_XYZ_EXECUTION_STATE_USER_ADDRESS=<public-user-address>`
- `SIS_TRADE_XYZ_EXECUTION_STATE_COLLECTOR_ENABLED=1`

再確認コマンド:

```bash
uv run sis execution-read-only-surfaces
uv run sis execution-snapshot --venue trade_xyz
uv run sis execution-drift-overview
uv run sis phase-gate-review
```

期待する読み方:

- public user address と opt-in がない状態では external API を呼ばず、`trade_xyz_execution_state_user_address_missing` または opt-in required として止まる。
- public user address と opt-in がある場合だけ account state / open orders / fills を read-only で読む。
- 成功しても wallet、signing、exchange write、live order の許可にはならない。

### Bitget demo read-only smoke

必要な入力:

- `BITGET_DEMO_API_KEY`
- `BITGET_DEMO_API_SECRET`
- `BITGET_DEMO_PASSPHRASE`

再確認コマンド:

```bash
uv run sis bitget-demo-smoke
uv run sis execution-read-only-surfaces
uv run sis execution-drift-overview
uv run sis phase-gate-review
```

期待する読み方:

- demo credentials は production Bitget futures readiness ではない。
- `bitget_demo` は demo 検証用 surface であり、Strategy Lab の正式 production venue ではない。
- smoke 成功は live order lifecycle や exchange write 許可ではない。

### Normal paper observation

必要な入力:

- 新しい trading day を含む通常 paper observation evidence。
- 同じ trading day の artifact rerun や fill 水増しは `10 trading days` の代替にしない。

再確認コマンド:

```bash
uv run sis strategy-paper-observation-status \
  --data-dir data \
  --out data/research/strategy_lifecycle \
  --reports-dir data/reports
```

期待する読み方:

- `latest_normal_requirement_gaps.trading_days` が進んだかを見る。
- `smoke_pass_counts_as_normal_pass=false` を維持する。
- `normal_thresholds_met=true` になるまで live readiness と読まない。

## Completed / Paused Candidate

### Strategy Review dogfood

`strategy-review-build` / `strategy-review-record` の dogfood は `dogfood-operator-current` で実行済み。tracked 記録は [archive/2026-06-22-doc-routing/DOGFOOD_REVIEW_2026-06-16.md](archive/2026-06-22-doc-routing/DOGFOOD_REVIEW_2026-06-16.md) に historical snapshot として残す。

これは paper / live permission ではない。runtime hash は tracked doc に固定せず、`operator_review.yaml` と `strategy-review-record --validate-existing` で確認する。

### Paper observation status artifact

`strategy-paper-observation-status` は実装済み。出力は `data/research/strategy_lifecycle/paper_observation_status.json` と `data/reports/paper_observation_status.md`。

確認時は次を再実行し、`observation_state`、`next_action`、`normal_thresholds_met`、`latest_normal_requirement_gaps`、`smoke_pass_counts_as_normal_pass`、`live_conversion_allowed` を読む。

```bash
uv run sis strategy-paper-observation-status \
  --data-dir data \
  --out data/research/strategy_lifecycle \
  --reports-dir data/reports
```

注意: `normal_session_count` は通常sessionの数であり、通常threshold達成の代替証拠ではない。現行 review logic では、最新の通常session自体が `min_fills_for_pass` と `min_trading_days_for_pass` を満たした時だけ `normal_thresholds_met=true` になる。同じ trading day の fill を増やしても、10 trading days の代替証拠にはならない。

### `venue-read-only-probe`

`venue-read-only-probe` は実装済みで、dogfood decision は `NO_ACTION`。

これは Bitget / Hyperliquid production readiness、credentialed read-only network readiness、paper readiness、live readiness を証明しない。

実装計画と dogfood 記録は `plan/archive/2026-06-17-plan-routing/0609ここからの計画/03_venue_read_only_capability_probe/` に archive 済み。現行 next action としては読まない。

### Operations / audit / remediation refresh

operations / audit / remediation 系の生成物は runtime artifact なので、この文書に固定値を写さない。確認時は次を再実行し、生成物の `overall_status`、`monitoring_status`、execution gap、readiness gap、`strict_validation_issue_count` を読む。

```bash
uv run sis refresh-operations-artifacts
uv run sis operations-dashboard
uv run sis readiness-snapshot
uv run sis execution-snapshot --venue trade_xyz
uv run sis execution-drift-overview
uv run sis validate-artifacts --strict
uv run sis phase-gate-review
```

Trade[XYZ] は read-only execution state collector contract 実装済みだが、通常実行では external API を使わず、public user address 未設定として止まる。未設定時の execution gap は `trade_xyz_execution_state_user_address_missing` と `set_trade_xyz_execution_state_public_user_address` を見る。Bitget demo は demo credentials と read-only network probe の有無を別に確認する。

これは read-only / paper gate の失敗とは別に読む。`phase-gate-review` が通過系に見えても、それは execution readiness や live readiness の証明ではない。`check-go-no-go` と evidence card は補助 report であり、live readiness の正本ではない。

## Not On Current Roadmap

次は現行 roadmap には入れません。実施するなら別計画、承認、stop condition が必要です。

- production live trading
- wallet / signing
- exchange write
- Bitget futures / Hyperliquid perp を Strategy Lab schema に入れること
- backtest pass から paper ready / live ready を主張すること
- `READ_ONLY_GO` を live ready と読むこと
- `catalog known` を venue enabled と読むこと
- `read-only probe` を network readiness と読むこと

## 誤読防止

- `計画あり` は `実装決定` ではない。
- `catalog known` は `venue enabled` ではない。
- `read-only probe` は `network readiness` ではない。
- `PAPER_OBSERVATION_CANDIDATE` は paper 実行許可ではない。
- `READ_ONLY_GO` は live ready ではない。
- fixed public command count は current truth ではない。確認時点で `uv run sis --help` を再実行する。
