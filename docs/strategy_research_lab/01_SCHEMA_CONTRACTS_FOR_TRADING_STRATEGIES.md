# Schema Contracts For Trading Strategies

この文書は、Strategy Research Lab が売買に関わる戦略を扱う時の schema 契約です。JSON Schema は外部 artifact guard と interoperability 用の薄い契約で、詳細な runtime validation は Pydantic model が正本です。

## 正本の読み順

1. `src/sis/research/strategy_lab/`
2. `src/sis/research_protocol/`
3. `schemas/*.v1.schema.json`
4. `tests/test_strategy_lab_*.py`, `tests/test_strategy_run_profile.py`, `tests/test_paper_from_intents.py`

## Claim guard

現行 claim 名はすべて `*_claimed` です。

```text
profitability_claimed
paper_ready_claimed
tiny_live_ready_claimed
live_ready_claimed
```

`profitability_claim`, `paper_ready_claim`, `tiny_live_ready_claim`, `live_ready_claim` は legacy name であり、`StrategyExperimentSpec` と `StrategyRunProfile` では拒否されます。

## SymbolBinding

目的: execution venue 上の取引シンボルと、実市場データ側のシンボルを明示的に分ける。

主要 field:

- `execution_venue`: 現行は `trade_xyz`。
- `execution_symbol`: Trade[XYZ] 側で扱う取引シンボル。空文字禁止。保存時に大文字化。
- `real_market_symbol`: feature / tracking 側で使う実市場シンボル。空文字禁止。保存時に大文字化。
- `asset_class`: `basket_index`, `index`, `equity` など。
- `country`: 任意。
- `currency`: default `USD`。

proxy rule:

- `XYZ100` は `QQQ` に binding する。
- `SP500` は `SPY` に binding する。

売買上の意味:

- `execution_symbol` は paper intent や execution-side quote lookup に使われる。
- `real_market_symbol` は特徴量、外部市場データ、tracking で使われる。
- ここを曖昧にすると、QQQ由来のsignalをXYZ100で執行するのか、XYZ100自体の時系列で予測したのかが混ざる。

## StrategyExperimentSpec

目的: 戦略仮説と実験条件を定義する。売買候補ではない。

主要 field:

- `schema_version`: `strategy_experiment_spec.v1`
- `strategy_id`: 例 `equity_index_momentum_v0`
- `strategy_family`: 例 `momentum`, `mean_reversion`, `breakout`
- `strategy_version`: 例 `v0`
- `enabled`
- `description`
- `symbol_bindings`
- `generator_id`
- `parameter_grid`
- `evaluation_plan_id`
- `run_profile_id`
- `forbidden_claims`

validation:

- `symbol_bindings` は1件以上。
- `strategy_id`, `strategy_family`, `strategy_version`, `generator_id` は空文字禁止。
- `forbidden_claims` は `DEFAULT_FORBIDDEN_CLAIMS` をすべて含む。
- legacy claim name は拒否される。

売買上の意味:

- これは「何を観測し、どんな条件でsignalを作り、どのsymbolに対応させるか」の契約です。
- ここには order size、wallet、exchange write、live ready 判断を書かない。
- `parameter_grid` は研究用の探索範囲であり、運用パラメータの確定値ではない。`strategy-experiment-run --spec` では safe cartesian sweep として展開される。

現行制約:

- default generator は `qqq_trend_rates_vix`。
- registered generator は `qqq_trend_rates_vix`, `sp500_trend_rates_vix`。
- `strategy-experiment-run --spec path/to/spec.yaml` は任意の `StrategyExperimentSpec` YAML/JSON を読み、登録済み `generator_id` の build 関数を spec の lineage で実行できる。
- `parameter_grid` は cartesian 展開され、各 variant の signal には `parameter_hash` と `parameter_grid:<hash>` reason code が付く。`--max-variants` 超過、空の grid value、未登録 generator は fail closed で止まる。
- 現行 built-in generator は `min_source_confidence`, `max_vix_level` / `vix_gate`, `min_research_return_1d`, `timeframe` を signal 条件または出力 timeframe として消費できる。その他の key は lineage/hash に残るが、built-in generator の条件には使われない。

## StrategySignalRecord

目的: generator が作った strategy signal row を保存する。

canonical artifact:

- `data/research/strategy_signals.parquet`
- `data/research/strategy_signal_manifest.json`
- `data/research/strategy_signals.jsonl` は line-delimited export。
- `data/research/signals.csv` は legacy export。Strategy Lab 正本ではない。

主要 field:

- `schema_version`: `strategy_signal.v1`
- `signal_id`, `generated_at`
- `strategy_id`, `strategy_family`, `strategy_version`
- `trial_id`, `parameter_hash`
- `ts_signal`, `timeframe`
- `execution_venue`, `execution_symbol`, `real_market_symbol`
- `side`: `long`, `short`, `close`, `reduce`, `add`, `rebalance`, `none`
- `raw_score`, `rank_score`, `percentile_rank`
- `tail_bucket`: `top`, `middle`, `bottom`, `none`
- `confidence`, `source_confidence`, `venue_quality_score`
- `feature_snapshot_ref`, `quote_ref`, `tracking_ref`
- `reason_codes`, `block_reasons`

validation:

- `execution_symbol`, `real_market_symbol` は空文字禁止、大文字化。
- 現行 CLI は `signal_id` が空または重複している signal artifact を evaluation 前に止める。
- `confidence` は 0.0 から 1.0。
- `rank_score`, `percentile_rank` は存在する場合 0.0 から 1.0。
- `validate_strategy_signal_frame()` は必須 column と `SymbolBinding` 一致を確認する。

manifest:

- `schema_version`: `strategy_signal_manifest.v1`
- `generator_id`, `strategy_id`, `strategy_family`, `strategy_version`
- `symbol_bindings`
- `feature_panel_sha256`
- `signal_count`
- `signal_artifact_run_id`
- no-signal 時も generator metadata と feature fingerprint を保持する。

売買上の意味:

- `side=long/short/close/reduce/add/rebalance/none` は売買方向または paper close / reduce / add / rebalance marker の候補であり、まだ order action ではない。
- `rank_score`, `percentile_rank`, `tail_bucket` は候補選別用の相対評価です。単独で収益性を証明しない。
- `source_confidence` と `venue_quality_score` は data/venue quality gate へ接続するための情報です。

## EvaluationPlan

目的: 評価窓、purge / embargo、必要データ、コスト stress、合格 metric を固定する。

主要 field:

- `schema_version`: `evaluation_plan.mls.v1`
- `evaluation_plan_id`
- `run_profile`: `strategy_lab`, `walkforward_research`, `paper_candidate`
- `target_venue`: `trade_xyz`
- `split_method`: `single_window`, `walk_forward`, `purged_walk_forward`
- `label_horizon_minutes`, `purge_minutes`, `embargo_minutes`
- `era_unit`: `session`, `trading_day`, `week`, `month`
- `quote_data_path`, `feature_panel_path`, `tracking_data_path`, `cost_model_path`
- `require_tracking_gate`, `require_source_confidence`, `require_venue_quality`
- `min_trade_count`, `max_turnover`
- `cost_stress_multiplier`, `slippage_stress_multiplier`
- `primary_metric`, `secondary_metrics`
- `forbidden_claims`

validation:

- horizon / purge / embargo / min trade count は positive。
- cost / slippage stress multiplier は 1.0 以上。
- `forbidden_claims` は current `*_claimed` names をすべて含む。

売買上の意味:

- `EvaluationPlan` は「どのデータ範囲で、どの leakage 対策とコスト前提で評価したか」を固定する。
- promotion の前に、過剰最適化、未来情報混入、低サンプル、低品質 venue の混入を止める役割を持つ。

## TrialRecord / TrialLedger

目的: best trial だけでなく全 trial を append-only に記録する。

artifact:

- `data/research/trial_ledger.jsonl`

主要 field:

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
- claim flags: all false

validation:

- required IDs は空文字禁止。
- `trial_index >= 0`。
- `parameter_count > 0`。
- count 系は 0 以上。
- `profitability_claimed`, `paper_ready_claimed`, `tiny_live_ready_claimed`, `live_ready_claimed` は false。

売買上の意味:

- `selected_for_next_stage=true` は paper candidate pack に進める候補という意味で、paper-ready や live-ready ではない。
- `metrics` は評価結果の容器です。収益性主張をする場合は別途検証文脈が必要ですが、現行 model では収益性 claim は禁止です。
- 現行 CLI は同じ `trial_id` を重複追記しない。`metrics.signal_artifact_run_id` で signal artifact と接続する。
- `--rank-thresholds` は複数 TrialRecord を同一 `trial_group_id` に記録する paper-only parameter sweep です。
- `--split-method walk_forward` / `--era-unit` は era 別 signal count metrics を `metrics` に残す。PnL や live-ready 証明ではない。

## TradeCandidate

目的: Strategy Lab から paper candidate pack に渡す売買候補。まだ order ではない。

主要 field:

- `schema_version`: `trade_candidate.v1`
- `candidate_id`, `generated_at`
- `signal_id`, `strategy_id`, `trial_id`
- `execution_venue`, `execution_symbol`, `real_market_symbol`
- `side`, `timeframe`
- `status`: `candidate`, `blocked`, `no_signal`, `hold`
- `raw_score`, `rank_score`, `percentile_rank`, `tail_bucket`, `confidence`
- `unique_contribution_score`, `index_exposure_score`
- `entry_reason_codes`, `block_reasons`
- `feature_snapshot_ref`, `quote_ref`, `tracking_ref`
- `live_order_submitted=false`

validation:

- `candidate_id`, `strategy_id`, `execution_symbol`, `real_market_symbol` は空文字禁止。
- `live_order_submitted` は false。
- score / confidence は存在する場合 0.0 から 1.0。

売買上の意味:

- `side` は候補方向であり、まだ `enter`, `exit`, `reduce`, `skip` ではない。
- `status=blocked` は candidate pack 内に残せる。top-level `blocked_candidate_ids` は現行 code にはない。
- `entry_reason_codes` はなぜ候補化したか、`block_reasons` はなぜ止めたかの監査 trail です。

## PaperCandidatePack

目的: paper へ進める前の候補束。selected / rejected / blocked の判断材料を保持する。

artifact:

- `data/research/paper_candidate_pack.json`

主要 field:

- `schema_version`: `paper_candidate_pack.v1`
- `pack_id`, `generated_at`
- `evaluation_plan_id`, `data_snapshot_id`, `feature_snapshot_id`, `trial_group_id`
- `candidates`
- `selected_candidate_ids`
- `rejected_candidate_ids`
- `selection_policy`
- `reason_codes`
- `block_reasons`
- claim / live / wallet / exchange flags: all false

validation:

- selected / rejected ID は `candidates` 内に存在する。
- candidate ID、selected ID、rejected ID は重複禁止。
- `profitability_claimed`, `paper_ready_claimed`, `tiny_live_ready_claimed`, `live_ready_claimed` は false。
- `live_order_submitted`, `wallet_used`, `exchange_write_used` は false。

売買上の意味:

- pack は paper 観測に進める候補の束であり、注文束ではない。
- `selected_candidate_ids` は paper intent preview の候補ソースになる。
- `rejected_candidate_ids` と candidate-level `block_reasons` は、量産時の重複失敗を減らすための学習材料です。
- 現行 CLI は latest trial group を default で pack 化し、TrialRecord の `metrics.selected_signal_ids` から candidate を作る。
- default evaluation では最新 `ts_signal` の 1 signal だけを選ぶ。`--candidate-limit 0` を使うと threshold 通過 signal を複数 candidate 化できる。

## PromotionDecision

目的: `PaperIntentPreview` 生成前の人間判断 artifact。

artifact:

- `data/research/promotion_decision.json`

主要 field:

- `schema_version`: `promotion_decision.v1`
- `promotion_id`, `generated_at`
- `source_pack_id`
- `reviewer`
- `from_stage`: `strategy_lab`, `paper_candidate`
- `to_stage`: `paper_observation`, `micro_live_candidate`
- `decision`: `promote`, `reject`, `hold`
- `required_evidence`
- `observed_evidence`
- `approval_reasons`
- `rejection_reasons`
- paper/tiny/live/wallet/exchange flags: all false

validation:

- `promotion_id`, `source_pack_id` は空文字禁止。
- `decision=promote` は required evidence がすべて observed に含まれ、approval reason が必要。
- `decision=reject` / `hold` は rejection reason が必要。
- live/wallet/exchange flags は false。

売買上の意味:

- promotion は paper observation への許可であり、live trading への許可ではない。
- `to_stage=micro_live_candidate` は model 上の値として存在するが、現行の Strategy Lab から micro live への直接昇格 surface は未完成です。

## PaperIntentPreview

目的: paper 専用の仮注文意図。live order ではない。live 変換は禁止。

artifact:

- `data/bot/paper_intent_preview.json`

主要 field:

- `schema_version`: `paper_intent_preview.v1`
- `intent_id`, `generated_at`, `valid_until`
- `source_pack_id`, `candidate_id`, `strategy_id`
- `execution_venue`, `execution_symbol`, `real_market_symbol`
- `action`: `enter`, `exit`, `reduce`, `skip`
- `side`: `long`, `short`, `close`, `reduce`, `add`, `rebalance`, `none`
- `order_style`: `paper_taker`, `paper_maker`, `skip`
- `price_reference`: `best_bid`, `best_ask`, `mid`, `mark`, `oracle`
- `notional_usd`, `quantity`
- `source_quote_ts`, `source_tracking_ts`, `source_feature_ts`, `source_phase_gate_run_id`
- `requires_revalidation=true`
- `paper_only=true`
- `live_conversion_allowed=false`
- `live_order_submitted=false`
- `wallet_used=false`
- `exchange_write_used=false`

validation:

- identity fields は空文字禁止。
- `requires_revalidation` は true。
- `paper_only` は true。
- `live_conversion_allowed`, `live_order_submitted`, `wallet_used`, `exchange_write_used` は false。
- symbol は大文字化。

売買上の意味:

- ここで初めて `action` が出るが、これは paper runner へ渡す仮意図です。
- `paper-from-intents` は最新 quote、expiry、paper broker validation で再検証する。
- `notional_usd` は現行 paper runner の quantity 計算に直結していない。現行 runner は `quantity` が無ければ `1.0` を使うため、実運用仕様として誤読しない。

## DataSnapshotManifest

目的: どの data snapshot を使ったかを固定する。

主要 field:

- `schema_version`: `data_snapshot_manifest.v1`
- `data_snapshot_id`, `generated_at`
- `quote_data_path`, `quote_data_sha256`
- `feature_panel_path`, `feature_panel_sha256`
- `tracking_data_path`, `tracking_data_sha256`
- `phase_gate_summary_path`, `phase_gate_decision`
- `symbols`, `venues`
- `min_ts`, `max_ts`
- `data_quality_summary`

validation:

- `data_snapshot_id`, `quote_data_path`, `feature_panel_path` は空文字禁止。
- `symbols`, `venues` は空文字除外後も1件以上。
- `symbols` は大文字化。
- `min_ts <= max_ts`。

## FeatureSnapshotManifest

目的: feature panel の生成条件と leakage guard を固定する。

主要 field:

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

validation:

- identity / path / version / policy fields は空文字禁止。
- `missing_rate_by_feature` は 0.0 から 1.0。
