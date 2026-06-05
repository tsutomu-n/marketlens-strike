<!--
作成日: 2026-05-29_21:42 JST
更新日: 2026-06-05_08:11 JST
-->

# Component Cards

この付録は、戦略部品を Strategy Research Lab の実装済み component に対応させるカードです。旧 `ExecutionPlan(action, symbol, quantity, notes)` 中心の説明は legacy paper runner 内部 bridge として扱い、Strategy Lab の設計入口にはしません。

## StrategyExperimentSpec

役割:

- 戦略仮説と実験条件を固定する。

入力:

- strategy family
- symbol binding
- generator ID
- parameter grid
- evaluation plan ID
- run profile ID

出力:

- generator / evaluator が参照する実験契約

禁止:

- order quantity
- live-ready claim
- wallet / exchange write

## SymbolBinding

役割:

- execution symbol と real market symbol を分ける。

例:

- `XYZ100 -> QQQ`
- `SP500 -> SPY`

失敗モード:

- proxy 関係を失い、実市場 feature と execution venue quote が混ざる。

## SignalGeneratorRegistry

役割:

- signal generator を ID で登録・取得・実行する。

現行 generator:

- `qqq_trend_rates_vix`

失敗モード:

- 未登録 generator は fail closed。
- generator ID の重複登録は禁止。

## StrategySignalRecord

役割:

- generator が出した signal を canonical artifact にする。

artifact:

- `data/research/strategy_signals.parquet`

主な field:

- `side`
- `rank_score`
- `confidence`
- `source_confidence`
- `venue_quality_score`
- `reason_codes`
- `block_reasons`

禁止:

- signal を order とみなす。
- `signals.csv` を正本にする。

## EvaluationPlan

役割:

- 評価条件、leakage guard、cost stress、合格 metric を固定する。

主な field:

- split method
- horizon
- purge / embargo
- source confidence requirement
- venue quality requirement
- cost / slippage stress

失敗モード:

- 同一期間への過剰最適化。
- cost 無視。
- low-quality source の混入。

## TrialRecord / TrialLedger

役割:

- 全 trial を append-only に残す。

artifact:

- `data/research/trial_ledger.jsonl`

主な field:

- `trial_id`
- `parameter_hash`
- `data_snapshot_id`
- `feature_snapshot_id`
- `metrics`
- `selected_for_next_stage`
- `rejection_reasons`

禁止:

- best trial だけ残す。
- selected を paper-ready / live-ready と読む。

## TradeCandidate

役割:

- signal / trial 由来の売買候補を表す。

主な field:

- `candidate_id`
- `signal_id`
- `trial_id`
- `side`
- `status`
- `entry_reason_codes`
- `block_reasons`

禁止:

- paper order とみなす。
- live order とみなす。
- `live_order_submitted=true`。

## PaperCandidatePack

役割:

- paper に進める前の候補束を保持する。

artifact:

- `data/research/paper_candidate_pack.json`

主な field:

- `candidates`
- `selected_candidate_ids`
- `rejected_candidate_ids`
- `selection_policy`

禁止:

- `blocked_candidate_ids` がある前提で読む。
- profitability / paper-ready / live-ready claim を含める。

## PromotionDecision

役割:

- paper intent preview 生成前の人間判断 artifact。

decision:

- `promote`
- `reject`
- `hold`

主な guard:

- promote requires evidence
- hold/reject require rejection reason
- wallet / exchange write false

禁止:

- promote を live-ready と読む。

## PaperIntentPreview

役割:

- paper runner へ渡す仮注文意図。

artifact:

- `data/bot/paper_intent_preview.json`

必須 guard:

- `requires_revalidation=true`
- `paper_only=true`
- `live_conversion_allowed=false`
- `live_order_submitted=false`
- `wallet_used=false`
- `exchange_write_used=false`

禁止:

- live order とみなす。
- exchange adapter へ渡す。

## paper-from-intents

役割:

- PaperIntentPreview を latest quote と PaperBroker で再検証し、paper artifacts を作る。

出力:

- `data/paper/orders.parquet`
- `data/paper/fills.parquet`
- `data/paper/positions.parquet`
- `data/paper/paper_observation_ledger.jsonl`

block reason:

- `INTENT_EXPIRED`
- `LATEST_QUOTE_MISSING`
- `PAPER_BROKER_REVALIDATION_BLOCKED`

## DataSnapshotManifest

役割:

- quote / feature / tracking data の snapshot lineage を固定する。

主な field:

- `data_snapshot_id`
- paths and sha256
- symbols
- venues
- `min_ts`, `max_ts`
- data quality summary

## FeatureSnapshotManifest

役割:

- feature panel の build lineage と leakage guard を固定する。

主な field:

- `feature_snapshot_id`
- `input_data_snapshot_id`
- `feature_version`
- `feature_cutoff_policy`
- `leakage_checks`
- `missing_rate_by_feature`
