<!--
作成日: 2026-05-30_08:14 JST
更新日: 2026-06-18_02:42 JST
-->

# Strategy Research Lab Doc Audit And Spec 2026-05-30

この文書は、2026-05-30 時点の Strategy Research Lab の仕様監査と既存ドキュメント分類をまとめた履歴資料です。現行の入口ではありません。

関連する 2026-06-09 時点の全体 docs audit は `docs/archive/2026-06-17-doc-routing/DOCUMENT_AUDIT_2026-06-09_NDX_2_3_2_4_REFRESH.md` に archive 済み。現行の Strategy Lab 仕様と能力は `docs/strategy_research_lab/` から確認します。

## 結論

- Strategy Research Lab の主要 schema / Pydantic model / CLI surface は実装済み。
- ただし tracked JSON Schema は full contract ではなく、最低限の required / const guard を置く薄い契約である。詳細な runtime validation の正本は `src/sis/research/strategy_lab/` と `src/sis/research_protocol/` の Pydantic model。
- `data/research/signals.csv` / `ResearchSignalStrategy` / `DecisionContext` / `ExecutionPlan` 中心の文書は legacy paper path の説明であり、Strategy Research Lab の現行正本として読まない。
- `PaperIntentPreview` は paper-only の仮注文意図であり、live order へ変換してはいけない。`paper-from-intents` でも最新データで再検証される。
- NDX/QQQ family は research/backtest artifact として保持できるが、現行 paper path では `selected_candidate_ids`、`PaperIntentPreview`、raw intent JSON、legacy `paper-step` order generation の各境界で fail closed する。

## Code Truth

正本として確認する順番:

1. `src/sis/research/strategy_lab/`
2. `src/sis/commands/research.py`
3. `src/sis/commands/paper.py`
4. `src/sis/paper/runner.py`
5. `src/sis/research_protocol/`
6. `src/sis/venues/suitability.py`
7. `schemas/*.v1.schema.json`
8. `plan/marketlens_strategy_research_lab_migration_pack/` は historical implementation contract として読む

主要 model:

| Concept | Code | Schema |
|---|---|---|
| StrategyExperimentSpec / SymbolBinding / StrategySignalRecord | `src/sis/research/strategy_lab/specs.py` | `schemas/strategy_experiment_spec.v1.schema.json`, `schemas/strategy_signal.v1.schema.json` |
| StrategySignalManifest | `src/sis/research/strategy_lab/signal_artifact.py` | `schemas/strategy_signal_manifest.v1.schema.json` |
| EvaluationPlan | `src/sis/research/strategy_lab/evaluation_plan.py` | `schemas/evaluation_plan.mls.v1.schema.json` |
| TrialRecord / TrialLedger | `src/sis/research/strategy_lab/trial_ledger.py` | `schemas/trial_record.v1.schema.json` |
| TradeCandidate | `src/sis/research/strategy_lab/candidates.py` | `schemas/trade_candidate.v1.schema.json` |
| PaperCandidatePack | `src/sis/research/strategy_lab/paper_candidate_pack.py` | `schemas/paper_candidate_pack.v1.schema.json` |
| PromotionDecision | `src/sis/research/strategy_lab/promotion_decision.py` | `schemas/promotion_decision.v1.schema.json` |
| PaperIntentPreview | `src/sis/research/strategy_lab/paper_intent_preview.py` | `schemas/paper_intent_preview.v1.schema.json` |
| Venue suitability | `src/sis/venues/suitability.py` | runtime policy only; Strategy Lab schemas still allow only current `VenueId` values |
| DataSnapshotManifest | `src/sis/research_protocol/data_snapshot.py` | `schemas/data_snapshot_manifest.v1.schema.json` |
| FeatureSnapshotManifest | `src/sis/research_protocol/feature_snapshot.py` | `schemas/feature_snapshot_manifest.v1.schema.json` |

## Artifact Chain

Strategy Lab の artifact chain:

```text
StrategyExperimentSpec
  -> StrategySignalRecord rows in data/research/strategy_signals.parquet
  -> StrategySignalManifest in data/research/strategy_signal_manifest.json
  -> EvaluationPlan
  -> TrialRecord rows in data/research/trial_ledger.jsonl
  -> TradeCandidate rows inside PaperCandidatePack
  -> PromotionDecision
  -> PaperIntentPreview list in data/bot/paper_intent_preview.json
  -> paper-from-intents revalidation
  -> paper orders/fills/positions only
```

重要な分離:

- `TradeCandidate` は売買候補であり、paper order でも live order でもない。
- `PaperCandidatePack` は paper に送る候補束であり、`selected_candidate_ids` と `rejected_candidate_ids` を持つ。top-level の `blocked_candidate_ids` は現行コードには無い。blocked は `TradeCandidate.status="blocked"`、candidate の `block_reasons`、pack の `block_reasons` で表す。selected candidate は `status="candidate"`、空の `block_reasons`、venue-suitable でなければならない。
- `PromotionDecision` は人間判断 artifact。`decision="promote"` の場合は `required_evidence` がすべて `observed_evidence` に含まれ、`approval_reasons` が必要。
- `PaperIntentPreview` は paper 専用。`requires_revalidation=true`, `paper_only=true`, `live_conversion_allowed=false`, `live_order_submitted=false`, `wallet_used=false`, `exchange_write_used=false` が guard。venue suitability は preview model と `paper-from-intents` の raw JSON 再検証で掛かる。

## Schema Spec

### SymbolBinding

目的: Trade[XYZ] の execution symbol と real market symbol を分離する。

Fields:

- `execution_venue`: current Strategy Lab signal/candidate/intent schemas accept `trade_xyz` and `bitget_demo`; `bitget_futures` and `hyperliquid_perp` are not schema values in this slice.
- `execution_symbol`: Trade[XYZ] 側の取引シンボル。空文字は禁止。保存時は大文字化。
- `real_market_symbol`: feature / tracking 側の実市場シンボル。空文字は禁止。保存時は大文字化。
- `asset_class`
- `country`
- `currency`: default `USD`

Proxy rule:

- `XYZ100` は `QQQ` に binding する。
- `SP500` は `SPY` に binding する。

### StrategyExperimentSpec

目的: 戦略仮説と実験条件を定義する。売買候補ではない。

Required / important fields:

- `schema_version`: `strategy_experiment_spec.v1`
- `strategy_id`
- `strategy_family`
- `strategy_version`
- `enabled`
- `description`
- `symbol_bindings`
- `generator_id`
- `parameter_grid`
- `evaluation_plan_id`
- `run_profile_id`
- `forbidden_claims`

Validation:

- `symbol_bindings` は 1 件以上。
- `strategy_id`, `strategy_family`, `strategy_version`, `generator_id` は空文字禁止。
- `forbidden_claims` は `DEFAULT_FORBIDDEN_CLAIMS` をすべて含む。
- `DEFAULT_FORBIDDEN_CLAIMS` は `profitability_claimed`, `paper_ready_claimed`, `tiny_live_ready_claimed`, `live_ready_claimed`。
- `profitability_claim`, `paper_ready_claim`, `tiny_live_ready_claim`, `live_ready_claim` という古い claim 名は禁止。使うなら `*_claimed`。
- 現行 default generator は `qqq_trend_rates_vix`。registered generator は `qqq_trend_rates_vix`, `sp500_trend_rates_vix`。

### StrategySignalRecord

目的: 戦略 generator が作った signal row を保存する。canonical artifact は `data/research/strategy_signals.parquet`。必要に応じて jsonl export してよいが、旧 `data/research/signals.csv` を Strategy Lab 正本にしない。

Fields:

- `schema_version`: `strategy_signal.v1`
- `signal_id`, `generated_at`
- `strategy_id`, `strategy_family`, `strategy_version`
- `trial_id`, `parameter_hash`
- `ts_signal`, `timeframe`
- `execution_venue`, `execution_symbol`, `real_market_symbol`
- `side`: `long` / `short` / `none`
- `raw_score`, `rank_score`, `percentile_rank`
- `tail_bucket`: `top` / `middle` / `bottom` / `none`
- `confidence`, `source_confidence`, `venue_quality_score`
- `feature_snapshot_ref`, `quote_ref`, `tracking_ref`
- `reason_codes`, `block_reasons`

Validation:

- `execution_symbol` と `real_market_symbol` は空文字禁止、大文字化。
- `confidence`, `rank_score`, `percentile_rank` は 0.0 から 1.0 の範囲。

### EvaluationPlan

目的: 評価窓、purge / embargo、必要データ、コスト stress、合格 metric を固定する。

Fields:

- `schema_version`: `evaluation_plan.mls.v1`
- `evaluation_plan_id`
- `run_profile`: `strategy_lab` / `walkforward_research` / `paper_candidate`
- `target_venue`: `trade_xyz`
- `split_method`: `single_window` / `walk_forward` / `purged_walk_forward`
- `label_horizon_minutes`, `purge_minutes`, `embargo_minutes`
- `era_unit`: `session` / `trading_day` / `week` / `month`
- `quote_data_path`, `feature_panel_path`, `tracking_data_path`, `cost_model_path`
- `require_tracking_gate`, `require_source_confidence`, `require_venue_quality`
- `min_trade_count`, `max_turnover`
- `cost_stress_multiplier`, `slippage_stress_multiplier`
- `primary_metric`, `secondary_metrics`
- `forbidden_claims`

Validation:

- horizon / purge / embargo / min trade count は positive。
- cost / slippage stress multiplier は 1.0 以上。
- `forbidden_claims` は `DEFAULT_FORBIDDEN_CLAIMS` をすべて含む。
- `DEFAULT_FORBIDDEN_CLAIMS` は `*_claimed` 名で統一する。旧 `*_claim` 名は StrategyExperimentSpec / StrategyRunProfile では legacy name として拒否される。

### TrialRecord / TrialLedger

目的: best trial だけでなく全 trial を append-only に記録する。

Artifact:

- `data/research/trial_ledger.jsonl`

Fields:

- `schema_version`: `trial_record.v1`
- `trial_id`, `trial_group_id`, `trial_index`
- `strategy_id`, `strategy_family`, `strategy_version`
- `evaluation_plan_id`, `data_snapshot_id`, `feature_snapshot_id`
- `parameter_hash`, `parameter_count`, `parameter_space_hash`, `random_seed`, `git_sha`
- `signal_count`, `candidate_count`, `paper_candidate_count`, `executed_count`, `blocked_count`, `no_signal_count`
- `blocked_reason_counts`
- `metrics`
- `baseline_strategy_id`, `baseline_delta_metrics`
- `selected_for_next_stage`
- `rejection_reasons`
- `profitability_claimed=false`
- `paper_ready_claimed=false`
- `tiny_live_ready_claimed=false`
- `live_ready_claimed=false`

Validation:

- required IDs は空文字禁止。
- `trial_index >= 0`。
- `parameter_count > 0`。
- count 系は 0 以上。
- claim flags はすべて false のまま。

### TradeCandidate

目的: Strategy Lab から paper candidate pack に渡す売買候補。まだ order ではない。

Fields:

- `schema_version`: `trade_candidate.v1`
- `candidate_id`, `generated_at`
- `signal_id`, `strategy_id`, `trial_id`
- `execution_venue`, `execution_symbol`, `real_market_symbol`
- `side`, `timeframe`
- `status`: `candidate` / `blocked` / `no_signal` / `hold`
- `raw_score`, `rank_score`, `percentile_rank`, `tail_bucket`, `confidence`
- `unique_contribution_score`, `index_exposure_score`
- `entry_reason_codes`, `block_reasons`
- `feature_snapshot_ref`, `quote_ref`, `tracking_ref`
- `live_order_submitted=false`

Validation:

- `candidate_id`, `strategy_id`, `execution_symbol`, `real_market_symbol` は空文字禁止。
- `live_order_submitted` は false のまま。
- score / confidence は 0.0 から 1.0 の範囲。

### PaperCandidatePack

目的: paper へ進める前の候補束。selected / rejected / blocked の判断材料を保持する。

Fields:

- `schema_version`: `paper_candidate_pack.v1`
- `pack_id`, `generated_at`
- `evaluation_plan_id`, `data_snapshot_id`, `feature_snapshot_id`, `trial_group_id`
- `candidates`
- `selected_candidate_ids`
- `rejected_candidate_ids`
- `selection_policy`
- `reason_codes`
- `block_reasons`
- `profitability_claimed=false`
- `paper_ready_claimed=false`
- `tiny_live_ready_claimed=false`
- `live_ready_claimed=false`
- `live_order_submitted=false`
- `wallet_used=false`
- `exchange_write_used=false`

Validation:

- selected / rejected ID は `candidates` 内に存在する必要がある。
- selected / rejected ID と candidate ID は重複禁止。selected / rejected の重複も禁止。
- selected candidate は `status="candidate"`、空の `block_reasons`、venue-suitable でなければならない。
- claim / live / wallet / exchange flags は false のまま。
- 現行 code には top-level `blocked_candidate_ids` は無い。blocked は candidate status と reason fields で表す。

### PromotionDecision

目的: PaperIntentPreview 生成前の人間判断 artifact。

Fields:

- `schema_version`: `promotion_decision.v1`
- `promotion_id`, `generated_at`
- `source_pack_id`
- `reviewer`
- `from_stage`: `strategy_lab` / `paper_candidate`
- `to_stage`: `paper_observation` / `micro_live_candidate`
- `decision`: `promote` / `reject` / `hold`
- `required_evidence`
- `observed_evidence`
- `approval_reasons`
- `rejection_reasons`
- `paper_ready_claimed=false`
- `tiny_live_ready_claimed=false`
- `live_ready_claimed=false`
- `wallet_used=false`
- `exchange_write_used=false`

Validation:

- `promotion_id` と `source_pack_id` は空文字禁止。
- `paper_ready_claimed`, `tiny_live_ready_claimed`, `live_ready_claimed`, `wallet_used`, `exchange_write_used` は false のまま。
- `promote` は required evidence をすべて observed に含め、approval reason が必要。
- `reject` / `hold` は rejection reason が必要。

### PaperIntentPreview

目的: paper 専用の仮注文意図。live order ではない。live 変換禁止。

Fields:

- `schema_version`: `paper_intent_preview.v1`
- `intent_id`, `generated_at`, `valid_until`
- `source_pack_id`, `candidate_id`, `strategy_id`
- `execution_venue`, `execution_symbol`, `real_market_symbol`
- `action`: `enter` / `exit` / `reduce` / `skip`
- `side`: `long` / `short` / `none`
- `order_style`: `paper_taker` / `paper_maker` / `skip`
- `price_reference`: `best_bid` / `best_ask` / `mid` / `mark` / `oracle`
- `notional_usd`, `quantity`
- `source_quote_ts`, `source_tracking_ts`, `source_feature_ts`, `source_phase_gate_run_id`
- `requires_revalidation=true`
- `paper_only=true`
- `live_conversion_allowed=false`
- `live_order_submitted=false`
- `wallet_used=false`
- `exchange_write_used=false`

Validation:

- identity fields は空文字禁止。
- `requires_revalidation` と `paper_only` は true。
- live / wallet / exchange flags は false。
- venue suitability は `paper_intent` stage で再検査される。
- `paper-from-intents` はこの preview をそのまま信用せず、raw JSON を `PaperIntentPreview` model で再検証し、最新 quote / tracking / risk context でも再検証する。

### DataSnapshotManifest / FeatureSnapshotManifest

`DataSnapshotManifest` と `FeatureSnapshotManifest` は `src/sis/research_protocol/` に Pydantic model があり、JSON Schema も存在する。ただし JSON Schema は薄く、詳細 validation は Pydantic model が正本。

DataSnapshotManifest fields:

- `schema_version`: `data_snapshot_manifest.v1`
- `data_snapshot_id`, `generated_at`
- `quote_data_path`, `quote_data_sha256`
- `feature_panel_path`, `feature_panel_sha256`
- `tracking_data_path`, `tracking_data_sha256`
- `phase_gate_summary_path`, `phase_gate_decision`
- `symbols`, `venues`
- `min_ts`, `max_ts`
- `data_quality_summary`

DataSnapshotManifest validation:

- `data_snapshot_id`, `quote_data_path`, `feature_panel_path` は空文字禁止。
- `symbols` と `venues` は 1 件以上で、空文字を除外後も 1 件以上。
- `symbols` は大文字化。
- `min_ts` と `max_ts` が両方ある場合は `min_ts <= max_ts`。

FeatureSnapshotManifest fields:

- `schema_version`: `feature_snapshot_manifest.v1`
- `feature_snapshot_id`, `generated_at`
- `input_data_snapshot_id`
- `feature_panel_path`, `feature_panel_sha256`
- `feature_version`
- `feature_build_config_hash`
- `feature_cutoff_policy`
- `max_feature_source_ts`
- `leakage_checks`
- `missing_rate_by_feature`

FeatureSnapshotManifest validation:

- required identity / path / version / policy fields は空文字禁止。
- `missing_rate_by_feature` の値は 0.0 から 1.0 の範囲。

運用上は、TrialRecord の `data_snapshot_id` / `feature_snapshot_id` と、StrategySignalRecord / TradeCandidate の source refs を使って lineage を残す。

## CLI Workflow

Strategy Lab path:

```bash
uv run sis strategy-preview
uv run sis evaluate-strategy-lab
uv run sis build-paper-candidate-pack
uv run sis promotion-decision --decision hold
uv run sis build-paper-intent-preview
uv run sis paper-from-intents --intents-path data/bot/paper_intent_preview.json
```

重要:

- `strategy-preview` は `build_signals()` を通じて `data/research/strategy_signals.parquet`, `data/research/strategy_signals.jsonl`, legacy export `data/research/signals.csv`, `data/reports/strategy_signals_preview.md` を出す。
- `build_signals()` の default generator は `qqq_trend_rates_vix`。`--generator-id sp500_trend_rates_vix` で登録済み SP500 generator を選べる。`strategy-experiment-run --spec` は `StrategyExperimentSpec` YAML/JSON を読み込んで登録済み generator を spec lineage で実行し、`parameter_grid` を safe cartesian sweep として展開できる。現行 built-in generator は `min_source_confidence`, `max_vix_level` / `vix_gate`, `min_research_return_1d`, `timeframe` を signal 条件または出力 timeframe として消費できる。
- generator metadata は `SignalGeneratorDefinition` を正本にし、callable と `strategy_id`, `strategy_family`, `strategy_version`, `SymbolBinding` を同じ registry entry で管理する。
- generator は feature に `source_confidence` / `venue_quality_score` が存在する場合、Strategy Lab artifact まで pass-through する。存在しない場合は null として扱う。
- `build_signals()` は `strategy_signal_manifest.json` を書き、no-signal 時も empty schema と generator lineage を残す。
- `evaluate-strategy-lab` は `data/research/strategy_signals.parquet` が無い場合、empty artifact で manifest が無い場合、または 1 artifact 内に複数の strategy / symbol identity が混在する場合、exit code 2 で止まる。
- `evaluate-strategy-lab` は同じ `trial_id` を重複追記しない。
- `evaluate-strategy-lab --rank-thresholds 0.2,0.8` は同じ `trial_group_id` に threshold 別の `TrialRecord` を記録する。
- `evaluate-strategy-lab --candidate-limit 0` は threshold 通過 signal を複数 `metrics.selected_signal_ids` として記録できる。default は最新 `ts_signal` の 1 signal。
- `--split-method` / `--era-unit` は era 別 signal count metrics の記録であり、PnL や live-ready 証明ではない。
- `trial_id`, `trial_group_id`, `paper_candidate_pack.pack_id`, `promotion_id` は signal artifact content 由来の deterministic `run_id` で作る。
- `build-paper-candidate-pack` は default で latest trial group だけを使い、selected candidate は `TrialRecord.metrics.selected_signal_ids` から作る。古い group は `--trial-group-id` で明示する。
- `promotion-decision` は実際の `PaperCandidatePack.pack_id` を `source_pack_id` に保存し、`build-paper-intent-preview` は pack と decision の source mismatch を exit code 2 で止める。
- `promotion-decision` と `build-paper-intent-preview` は source pack が無い場合 exit code 2 で止まる。
- `build-paper-intent-preview` は `PromotionDecision` が無い場合 exit code 2 で止まる。
- `promotion-decision --decision promote` は required evidence が揃っていないと model validation で止まる。
- `paper-from-intents` は paper runner に渡すだけであり、live adapter には渡さない。

## Docs Audit

### 更新する docs

2026-05-30時点で、以下は実施済みまたは詳細仕様へ分離済みです。2026-06-09 時点の docs 全体の分類は `docs/archive/2026-06-17-doc-routing/DOCUMENT_AUDIT_2026-06-09_NDX_2_3_2_4_REFRESH.md` に archive 済みです。

| Path | 理由 | 更新方針 |
|---|---|---|
| `README.md` | read order が Trade[XYZ] / PR12 中心で Strategy Lab 正本が無い | 実施済み |
| `docs/CURRENT_STATE.md` | current state が read-only gate 中心で Strategy Lab 実装済み surface を含まない | 実施済み |
| `docs/CODE_STATUS.md` | PR-00 to PR-12 軸だけで Strategy Lab 実装済み status が無い | 実施済み |
| `docs/ARCHITECTURE_AND_PHASES.md` | research と paper の間の Strategy Lab artifact chain が抜けている | 実施済み |
| `docs/OPERATIONS_RUNBOOK.md` | operator が Strategy Lab -> paper-only path を実行する導線が無い | 実施済み |
| `docs/algo/README.md` | strategy design docs と implemented schema chain の橋が弱い | 実施済み |
| `docs/algo/strategy_factory/README.md` | factory の candidate sheet から StrategyExperimentSpec への接続が無い | 実施済み |

### 古い内容を含む docs

| Path | 古い内容 | 扱い |
|---|---|---|
| `docs/algo/obsidian_note_rewrites_2026-05-29/ONE_DOC_STRATEGY_TO_IMPLEMENTATION.md` | `data/research/signals.csv`, `DecisionContext`, `ExecutionPlan` 中心の implementation path | Strategy Lab chain 前提で全面更新済み |
| `docs/algo/obsidian_note_rewrites_2026-05-29/appendix_materials/01_PIPELINE_DIAGRAMS.md` | `data/research/signals.csv` を active signal artifact として描く | Strategy Lab diagram 前提へ更新済み |
| `docs/algo/obsidian_note_rewrites_2026-05-29/appendix_materials/03_REPO_IMPLEMENTATION_MAP.md` | legacy repo map が現行 Strategy Lab schema chain を含まない | Strategy Lab repo map へ更新済み |
| `docs/algo/obsidian_note_rewrites_2026-05-29/appendix_materials/02_COMPONENT_CARDS.md` | `ExecutionPlan(action, symbol, quantity, notes)` を中心にする | Strategy Lab component cards へ更新済み |
| `docs/algo/obsidian_note_rewrites_2026-05-29/appendix_materials/04_ARTIFACT_EXAMPLES.md` | Signal CSV / Decision Log 例が中心 | Strategy Lab artifact examples へ更新済み |
| `docs/algo/obsidian_note_rewrites_2026-05-29/appendix_materials/05_WORKED_EXAMPLE_TREND_PULLBACK.md` | Signal CSV /旧paper review前提 | Strategy Lab worked example へ更新済み |
| `docs/algo/obsidian_note_rewrites_2026-05-29/appendix_materials/09_CHECKLISTS_AND_TEMPLATES.md` | Signal CSV / decision log checklist が中心 | Strategy Lab schema checklist へ更新済み |

### 作り直したほうがいい docs

- `ONE_DOC_STRATEGY_TO_IMPLEMENTATION.md`: 更新済み。
- `appendix_materials/01_PIPELINE_DIAGRAMS.md`: 更新済み。
- `appendix_materials/02_COMPONENT_CARDS.md`: 更新済み。
- `appendix_materials/03_REPO_IMPLEMENTATION_MAP.md`: 更新済み。
- `appendix_materials/04_ARTIFACT_EXAMPLES.md`: 更新済み。
- `appendix_materials/05_WORKED_EXAMPLE_TREND_PULLBACK.md`: 更新済み。
- `appendix_materials/09_CHECKLISTS_AND_TEMPLATES.md`: 更新済み。

### アーカイブしてよい docs

物理削除ではなく、まず historical / superseded と明記して current read order から外す。

| Path | 扱い |
|---|---|
| `docs/archive/2026-05-30-doc-audit/DOCUMENT_AUDIT_2026-05-26.md` | historical audit |
| `docs/archive/2026-05-30-doc-audit/DOCUMENT_AUDIT_2026-05-27.md` | historical audit |
| `docs/archive/2026-05-30-doc-audit/DOCUMENT_AUDIT_2026-05-28.md` | historical audit |
| `docs/archive/2026-05-30-doc-audit/TRADE_XYZ_IMPLEMENTATION_STATUS_AUDIT_2026-05-27.md` | historical Trade[XYZ] audit |
| `docs/archive/2026-06-05-doc-cleanup/TRADE_XYZ_IMPLEMENTATION_STATUS_AUDIT_2026-05-28.md` | historical Trade[XYZ] audit |
| `docs/archive/2026-05-30-doc-audit/NEXT_IMPLEMENTATION_PLAN_AFTER_P0_P1_2026-05-28.md` | superseded plan |
| `docs/archive/2026-06-17-doc-routing/LIVE_READINESS_BLOCKER_DECOMPOSITION_PLAN_2026-05-29.md` | historical live-readiness blocker plan; do not use as current blocker source |

`plan/marketlens_strategy_research_lab_migration_pack/` は削除しない。これは実装前の詳細 contract と PR 分割の履歴であり、現行仕様の正本ではない。ただし `templates/` 配下は再利用されやすいため、現行 `*_claimed` claim guard 名へ更新して copy-safe に保つ。

## Stop Conditions

- `READ_ONLY_GO` を live-ready と読まない。
- `PaperIntentPreview` を live order / `OrderIntent` と読まない。
- `TradeCandidate` を paper order と読まない。
- `PromotionDecision` が無い状態で `PaperIntentPreview` を生成しない。
- JSON Schema の薄い guard だけで full validation 済みと扱わない。runtime は Pydantic model で検証する。
- `data/` artifact が無い場合、未実装とは判断しない。必要な command で再生成する。
