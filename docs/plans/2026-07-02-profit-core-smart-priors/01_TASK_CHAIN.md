<!--
作成日: 2026-07-02_00:00 JST
更新日: 2026-07-02_00:00 JST
-->

# Task Chain: Profit Core Smart Priors

## 結論

このタスクチェーンは、コーダーが上から順に実装すれば、Smart Edge Candidate Factory から Virtual Execution Gate までの初期Coreを完了できる粒度に分解する。実装は一気に全部を作らず、T0からT9までを順に進める。各タスクは目的、対象ファイル、実装内容、テスト、完了条件を持つ。

## 共通制約

すべてのタスクに次を適用する。

1. paper / live / wallet / signing / production exchange write permission を出さない。
2. generated candidate は常に未検証候補として扱う。
3. selected-only outputを禁止する。
4. virtual PnLをactual cashと混ぜない。
5. `data/` はruntime stateであり、tracked source of truthにしない。
6. 依存追加はT0からT6では禁止する。
7. LLMを使う場合でも、LLMはadversarial findingだけを出し、gate overrideをしない。

## T0: Plan routing and docs baseline

### 目的

この計画一式をcurrent docsの品質基準に合わせ、後続実装の入口を固定する。

### 対象ファイル

- `docs/plans/2026-07-02-profit-core-smart-priors/README.md`
- `docs/plans/2026-07-02-profit-core-smart-priors/01_TASK_CHAIN.md`
- `docs/plans/2026-07-02-profit-core-smart-priors/02_ARTIFACT_CONTRACTS.md`
- `docs/plans/2026-07-02-profit-core-smart-priors/03_TEST_AND_ACCEPTANCE.md`
- `docs/plans/2026-07-02-profit-core-smart-priors/04_RESEARCH_BASIS.md`

### 実装内容

1. すべてのMarkdownに metadata header を置く。
2. final newline を維持する。
3. 固定pass countや固定command countを書かない。
4. runtime artifactの値をcurrent truthとして書かない。
5. 既存docsへのリンクは壊さない。迷う場合はリンクではなくbacktick pathにする。

### テスト

```bash
uv run python scripts/check_current_docs.py
git diff --check
```

### 完了条件

- current-docs checker が通る。
- docsが実装済みでない機能を実装済みと書いていない。

## T1: New package skeleton

### 目的

Smart Edge Candidate Factory を既存 `strategy_idea_candidates` から分け、責務を明確にする。

### 対象ファイル

新規:

- `src/sis/edge_candidate_factory/__init__.py`
- `src/sis/edge_candidate_factory/models.py`
- `src/sis/edge_candidate_factory/smart_priors.py`
- `src/sis/edge_candidate_factory/multiplicity.py`
- `src/sis/edge_candidate_factory/generator.py`
- `src/sis/edge_candidate_factory/ledger.py`
- `src/sis/edge_candidate_factory/backtest_kill_gate.py`
- `src/sis/edge_candidate_factory/virtual_execution_gate.py`
- `src/sis/commands/edge_candidate_factory.py`

変更:

- `src/sis/cli.py`
- `docs/REPO_CLI_CATALOG_CURRENT_2026-06-17.md`
- `scripts/check_current_docs.py` は原則変更しない。新docsが `docs/plans` 配下なら既に対象です。

### 実装内容

1. `edge_candidate_factory` moduleを作る。
2. CLI registrationを `src/sis/cli.py` に追加する。
3. public commandは最初は3つに絞る。

```text
edge-candidate-factory-run
edge-candidate-backtest-kill-gate
edge-candidate-artifact-summary
```

4. Virtual Execution Gate commandはT6まで追加しない。先にartifact contractとfixture testsを固める。

### テスト

```bash
uv run sis --help
uv run python scripts/check_cli_catalog.py
uv run ruff check src/sis/edge_candidate_factory src/sis/commands/edge_candidate_factory.py
```

### 完了条件

- `uv run sis --help` に新commandが出る。
- CLI catalog checkerが通る。
- まだ外部APIやcredentialを使わない。

## T2: Schema and model contracts

### 目的

候補生成より先に、候補・探索・会計・kill gate・virtual gateの保存形式を固定する。

### 対象ファイル

新規schema:

- `schemas/smart_candidate_prior_report.v1.schema.json`
- `schemas/edge_candidate_search_ledger.v1.schema.json`
- `schemas/trial_multiplicity_account.v1.schema.json`
- `schemas/backtest_kill_gate.v1.schema.json`
- `schemas/virtual_execution_gate.v1.schema.json`
- `schemas/llm_adversarial_evidence_review.v1.schema.json`

新規tests:

- `tests/edge_candidate_factory/test_models.py`
- `tests/edge_candidate_factory/test_schema_validation.py`

### 実装内容

`models.py` に最低限次のPydantic modelを定義する。

- `SmartCandidatePriorReport`
- `SmartCandidateCard`
- `CandidateMechanismCard`
- `CandidateSourceRequirement`
- `CandidateExecutionPrecheck`
- `CandidatePriorScore`
- `EdgeCandidateSearchLedger`
- `EdgeCandidateSearchLedgerRow`
- `TrialMultiplicityAccount`
- `BacktestKillGate`
- `VirtualExecutionGate`
- `LLMAdversarialEvidenceReview`

必須boundary:

```text
paper_execution_allowed=false
live_allowed=false
wallet_allowed=false
signing_allowed=false
production_exchange_write_allowed=false
auto_promote=false
```

### テスト

```bash
uv run pytest tests/edge_candidate_factory/test_models.py -q
uv run pytest tests/edge_candidate_factory/test_schema_validation.py -q
```

### 完了条件

- JSON Schema が Draft 2020-12 としてvalid。
- Pydantic dump が各schemaを通る。
- `extra="forbid"` 相当で不要fieldを落とす。
- boundary true flagが混入したらvalidationで落とす。

## T3: Smart Prior taxonomy and candidate cards

### 目的

feature listではなく、flow cause から候補を作る。

### 対象ファイル

- `src/sis/edge_candidate_factory/smart_priors.py`
- `tests/edge_candidate_factory/test_smart_priors.py`
- `docs/plans/2026-07-02-profit-core-smart-priors/02_ARTIFACT_CONTRACTS.md`

### 実装内容

`smart_priors.py` に次のtaxonomyを固定する。

```text
FORCED_FLOW
INVENTORY_RISK_TRANSFER
SLOW_INFORMATION
CONSTRAINED_ARBITRAGE
CROWDED_POSITIONING
BEHAVIORAL_ATTENTION
ADVERSE_SELECTION
EXECUTION_FRICTION
DATA_OBSERVABILITY
```

各priorは次を持つ。

- `cause_prior`
- `mechanism_template`
- `allowed_observables`
- `default_action_set`
- `required_sources`
- `default_execution_precheck`
- `default_kill_conditions`
- `expected_information_gain_template`

最初のfamily:

```text
funding_pressure_reversion
mark_index_basis_reversion
liquidation_exhaustion_reversal
liquidation_cascade_continuation
oi_impulse_continuation
volume_shock_reversal
volatility_compression_breakout
spread_widening_no_trade
funding_window_avoidance
cross_market_basis_dislocation
```

### テスト

```bash
uv run pytest tests/edge_candidate_factory/test_smart_priors.py -q
```

### 完了条件

- 各familyがcause priorを1つ以上持つ。
- 各familyがkill conditionを1つ以上持つ。
- 各familyがrequired sourceを1つ以上持つ。
- `volatility_compression_breakout` は standalone structural cause ではなく regime/statistical state として記録する。
- `spread_widening_no_trade` は trade action ではなく no-trade / filter family として出る。

## T4: Edge Candidate Factory v0

### 目的

実データsourceから、未検証候補を重複管理つきで生成する。

### 対象ファイル

- `src/sis/edge_candidate_factory/generator.py`
- `src/sis/edge_candidate_factory/ledger.py`
- `src/sis/commands/edge_candidate_factory.py`
- `tests/edge_candidate_factory/test_generator.py`
- `tests/edge_candidate_factory/test_cli.py`

### 入力

v0では次の入力形式を受ける。

```text
--source-root <prep-watchdeck-compatible-root>
--symbol BTCUSDT
--product-type USDT-FUTURES
--timeframe 5m
--family <repeatable>
--candidate-cap <int>
--out <path>
--replace-existing / --no-replace-existing
```

入力sourceは最初は `strategy-idea-candidates-bitget-source-refresh` が作る `source_root` と互換にする。source adapterは既存 `src/sis/strategy_idea_candidates/prep_watchdeck_source.py` の責務を再利用するか、薄いwrapperを作る。

### 出力

```text
smart_candidate_prior_report.json
smart_candidate_prior_report.md
edge_candidate_search_ledger.jsonl
trial_multiplicity_account.json
candidate_rejections.jsonl
candidate_summary.json
```

### 実装内容

1. 入力sourceを読み、symbolごとのcontract/ticker/candle availabilityを確認する。
2. sourceがない場合は candidateを作らず、`BLOCKED_SOURCE_REQUIREMENT` を出す。
3. familyごとに有限parameter gridを生成する。
4. 候補ごとに `SmartCandidateCard` を作る。
5. duplicate / near-duplicate候補はsilent dropせず、rejection ledgerに残す。
6. candidate cap超過もrejectionとして保存する。
7. `candidate_prior_score` は利益予測ではなく検証価値スコアとして計算する。
8. `success_only_reporting=false` を固定する。

### score v0

v0のscoreは単純な加点減点でよい。

```text
candidate_prior_score =
  mechanism_score
  + source_availability_score
  + execution_feasibility_score
  + testability_score
  + diversity_score
  + information_gain_score
  - operator_cost_penalty
  - unexecutable_penalty
  - overfit_surface_penalty
```

### テスト

```bash
uv run pytest tests/edge_candidate_factory/test_generator.py -q
uv run pytest tests/edge_candidate_factory/test_cli.py -q
```

### 完了条件

- 同じinputとconfigから同じcandidate IDsが出る。
- 全候補と全棄却が保存される。
- source不足時に候補を成功扱いしない。
- `candidate_prior_score` を alpha / profit proof と呼ばない。
- CLI stdoutに `network_attempted=false`, `exchange_write_used=false`, `live_order_submitted=false` を出す。

## T5: Trial Multiplicity Account v0

### 目的

大量候補生成を過剰最適化会計なしに進めない。

### 対象ファイル

- `src/sis/edge_candidate_factory/multiplicity.py`
- `tests/edge_candidate_factory/test_multiplicity.py`

### 実装内容

`TrialMultiplicityAccount` に次を保存する。

- `candidate_count_total`
- `candidate_count_shortlisted`
- `candidate_count_rejected`
- `family_count`
- `family_trial_counts`
- `parameter_grid_hashes`
- `effective_trial_count_status`
- `effective_trial_count`
- `candidate_cluster_count`
- `validation_peek_count`
- `rerank_count`
- `sealed_test_used_for_selection=false`
- `success_only_reporting=false`
- `adjustment_status`
- `known_gaps`

v0では候補間return correlationが未計算なら、`effective_trial_count_status=NOT_ESTIMABLE` とし、candidate countを保守的な上限として使う。

### テスト

```bash
uv run pytest tests/edge_candidate_factory/test_multiplicity.py -q
```

### 完了条件

- selected-only artifactを検出して失敗する。
- `sealed_test_used_for_selection=true` は失敗する。
- `validation_peek_count` と `rerank_count` が保存される。
- `effective_trial_count` が未計算でも、`NOT_ESTIMABLE` として明示される。

## T6: Backtest Kill Gate v0

### 目的

Backtestを攻める許可ではなく、大量候補を殺す装置にする。

### 対象ファイル

- `src/sis/edge_candidate_factory/backtest_kill_gate.py`
- `src/sis/commands/edge_candidate_factory.py`
- `tests/edge_candidate_factory/test_backtest_kill_gate.py`

### 入力

v0では、candidate-scoped backtest pack validation、candidate metrics、multiplicity account、source summaryを読む。C9 v0 bridge outputsが存在する場合はそれをsource refsとして使う。

### status

```text
KILL
INCONCLUSIVE_DATA
RESEARCH_ONLY
SHORTLIST_FOR_VIRTUAL
```

### 条件

最低限次を評価する。

- source availability。
- event count。
- closed trade count。
- after-cost edge over NO_TRADE。
- stress edge over NO_TRADE。
- largest loss。
- profit concentration。
- family-specific event threshold。
- multiplicity adjustment status。
- C9 bridge status。
- unexecutable reason count。

### family別event threshold

一律 `event_count >= 100` にしない。

```text
common_rule: 100
medium_event: 30
rare_dislocation: 10 plus RESEARCH_ONLY unless virtual/actual evidence exists
```

### テスト

```bash
uv run pytest tests/edge_candidate_factory/test_backtest_kill_gate.py -q
```

### 完了条件

- backtest passだけでは `SHORTLIST_FOR_VIRTUAL` にならない。
- `NO_TRADE` に負ける候補は `KILL` または `RESEARCH_ONLY` になる。
- source不足は `INCONCLUSIVE_DATA` になる。
- rare event family はevent countだけで即KILLせず、`RESEARCH_ONLY` に落とせる。
- gate artifactは `paper_execution_allowed=false`, `live_allowed=false` を固定する。

## T7: Candidate-to-Backtest Bridge hardening

### 目的

C9 bridgeをtechnical bridgeとeconomic gateに分け、`BRIDGED` の誤読を止める。

### 対象ファイル

- `src/sis/strategy_idea_candidates/authoring_bridge.py`
- `tests/strategy_idea_candidates/test_authoring_bridge.py`
- `docs/strategy_idea_candidates/GOAL_AND_GLOSSARY.md`
- 必要なら `schemas/strategy_idea_candidate_authoring_bridge.v1.schema.json`

### 実装内容

C9 v0の既存statusを維持しつつ、summaryに次を追加する。

- `technical_bridged_count`
- `economic_gate_ready_count`
- `economic_gate_not_evaluated_count`
- `actual_cash_ready_count`
- `actual_cash_missing_count`
- `bridge_success_semantics=technical_only`

可能ならstatusを増やす。

```text
BRIDGED_TECHNICAL_ONLY
BLOCKED_ECONOMIC_GATE
```

既存互換のため、`BRIDGED` をすぐ廃止しない。`BRIDGED` はtechnical statusであるとmanifestに明記する。

### テスト

```bash
uv run pytest tests/strategy_idea_candidates/test_authoring_bridge.py -q
```

### 完了条件

- `BRIDGED` がprofit proofではないことをmanifestに保存する。
- candidate-scoped paths/hashが失われない。
- default example backtestをcandidate proofとして流用しない。
- `min_trade_count: 0` や `pass_thresholds: {}` の場合、economic gateは `NOT_EVALUATED` と明記する。

## T8: Virtual Execution Gate v0

### 目的

actual cash前に、demo/testnet/fixtureでorder lifecycleとreconciliationを検証する。

### 対象ファイル

- `src/sis/edge_candidate_factory/virtual_execution_gate.py`
- `src/sis/commands/edge_candidate_factory.py`
- `tests/edge_candidate_factory/test_virtual_execution_gate.py`

必要になった場合のvenue-specific module:

- `src/sis/execution/bitget_demo_virtual.py`
- `tests/execution/test_bitget_demo_virtual.py`

### v0方針

1. まずfixture/mock modeを実装する。
2. Bitget demo network modeは明示opt-inがある場合だけ実装する。
3. Hyperliquid testnet / GRVT testnetはv0には入れない。
4. Virtual PnLをactual cashにしない。

### status

```text
VIRTUAL_NOT_RUN
VIRTUAL_BLOCKED_SOURCE
VIRTUAL_BLOCKED_EXECUTION_PRECHECK
VIRTUAL_FAILED_ORDER_LIFECYCLE
VIRTUAL_FAILED_RECONCILIATION
VIRTUAL_PASSED_EXECUTION_LIFECYCLE
```

### 必須field

```text
execution_environment=fixture | demo | testnet
actual_cash=false
cash_metric_basis=virtual_exchange
production_exchange_write_used=false
permits_live_order=false
order_accepted
partial_fill_handled
cancel_handled
reject_reason_captured
reduce_only_close_checked
flat_reconciliation_status
fee_like_fields_captured
funding_like_fields_captured
duplicate_order_prevented
```

### テスト

```bash
uv run pytest tests/edge_candidate_factory/test_virtual_execution_gate.py -q
```

### 完了条件

- virtual passがactual cash passにならない。
- fixture modeでorder lifecycleの正常系と異常系が検証される。
- reconciliation mismatchはhard failureになる。
- stdoutに `production_exchange_write_used=false`, `live_order_submitted=false` が出る。

## T9: LLM Adversarial Evidence Review v0

### 目的

候補volume増加時のnarrative creep、overclaim、missing artifactを検出する。ただしLLMに許可判断をさせない。

### 対象ファイル

- `src/sis/edge_candidate_factory/adversarial_review.py`
- `src/sis/commands/edge_candidate_factory.py`
- `tests/edge_candidate_factory/test_adversarial_review.py`
- `schemas/llm_adversarial_evidence_review.v1.schema.json`

### 実装内容

v0では外部LLM APIを呼ばない。manual import / local packet方式にする。

Commands:

```text
edge-candidate-adversarial-packet-build
edge-candidate-adversarial-import
```

review output:

```text
ADVERSARIAL_FINDING
MISSING_ARTIFACT
CONTRADICTION
OVERCLAIM_FLAG
NO_TRADE_COMPARISON_MISSING
ACTUAL_CASH_CONFUSION
HUMAN_REVIEW_REQUIRED
```

### 禁止

- LLMによるapproval。
- LLMによるpaper/live permission。
- LLMによるactual cash判定。
- LLMによるgate override。

### テスト

```bash
uv run pytest tests/edge_candidate_factory/test_adversarial_review.py -q
```

### 完了条件

- manual responseにapproval文言があっても、artifactはpermissionを出さない。
- missing source refsがある場合、findingとして保存される。
- machine-checkableな欠落だけをhard blockerにできる。

## T10: Integration summary command

### 目的

日常運用で見る数値を減らす。

### 対象ファイル

- `src/sis/edge_candidate_factory/summary.py`
- `src/sis/commands/edge_candidate_factory.py`
- `tests/edge_candidate_factory/test_summary.py`

### command

```text
edge-candidate-artifact-summary
```

### 出力field

```text
core_status
next_action
candidate_count_total
candidate_count_rejected
shortlist_for_virtual_count
virtual_passed_count
actual_cash_ready_count
known_gap_count
top_blocker_reasons
production_exchange_write_used=false
live_order_allowed=false
```

### 完了条件

- 欠損artifactを `exists=false` として表示し、失敗しない。
- 日常判断に必要なstatusを1画面で読める。
- Addon結果をCore statusに混ぜない。

## 最終ローカル検証

全タスク完了時は次を実行する。

```bash
uv run python -V
uv run sis --help
uv run python scripts/check_cli_catalog.py
uv run python scripts/check_current_docs.py
uv run ruff check .
uv run ruff format --check .
uv run pyrefly check
uv run ty check src --python-version 3.13 --output-format concise
uv run pytest -q
./scripts/check
```

固定pass countは記録しない。作業時点で再実行して確認する。
