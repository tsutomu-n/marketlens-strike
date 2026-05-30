# Checklists And Templates

戦略検討時にそのまま使う作業用テンプレートです。現行 Strategy Research Lab の schema と artifact chain に合わせています。

## 1. Hypothesis Intake

```md
# Hypothesis: <name>

- one sentence:
- strategy_family:
- execution_venue:
- execution_symbol:
- real_market_symbol:
- timeframe:
- expected edge:
- why it may persist:
- how it fails:
- baseline_strategy_id:
- required feature columns:
- required quote/tracking fields:
- no-trade conditions:
- source notes:
- decision: draft | ready-for-spec | reject
```

## 2. StrategyExperimentSpec Draft

```md
# StrategyExperimentSpec Draft

- schema_version: strategy_experiment_spec.v1
- strategy_id:
- strategy_family:
- strategy_version:
- enabled: true | false
- description:
- symbol_bindings:
  - execution_venue: trade_xyz
  - execution_symbol:
  - real_market_symbol:
  - asset_class:
  - country:
  - currency: USD
- generator_id:
- parameter_grid:
- evaluation_plan_id:
- run_profile_id: strategy_lab
- forbidden_claims:
  - profitability_claimed
  - paper_ready_claimed
  - tiny_live_ready_claimed
  - live_ready_claimed
```

Checklist:

- `XYZ100` は `QQQ` に binding している。
- `SP500` は `SPY` に binding している。
- generator ID は registry に存在する。
- legacy `*_claim` 名ではなく current `*_claimed` 名を使う。
- order quantity、wallet、exchange write を書いていない。

## 3. Signal Output Checklist

- canonical artifact は `data/research/strategy_signals.parquet`。
- `data/research/signals.csv` は legacy export としてだけ扱う。
- required columns がある。
- `execution_symbol` と `real_market_symbol` がある。
- `side` は `long | short | none`。
- `confidence` は 0.0 から 1.0。
- `rank_score` / `percentile_rank` は存在する場合 0.0 から 1.0。
- `tail_bucket` は `top | middle | bottom | none`。
- `reason_codes` が候補理由として読める。
- `block_reasons` が停止理由として読める。
- signal を order action として扱っていない。

## 4. EvaluationPlan Checklist

```md
# EvaluationPlan Draft

- schema_version: evaluation_plan.mls.v1
- evaluation_plan_id:
- run_profile: strategy_lab
- target_venue: trade_xyz
- split_method: single_window | walk_forward | purged_walk_forward
- label_horizon_minutes:
- purge_minutes:
- embargo_minutes:
- era_unit: session | trading_day | week | month
- quote_data_path:
- feature_panel_path:
- tracking_data_path:
- cost_model_path:
- require_tracking_gate:
- require_source_confidence:
- require_venue_quality:
- min_trade_count:
- max_turnover:
- cost_stress_multiplier:
- slippage_stress_multiplier:
- primary_metric:
- secondary_metrics:
- forbidden_claims:
```

Checklist:

- horizon / purge / embargo が positive。
- cost / slippage stress multiplier が 1.0 以上。
- baseline がある。
- leakage check がある。
- reject rules が評価前に書かれている。
- paper-ready / live-ready を主張していない。

## 5. Trial Ledger Review Template

```md
# Trial Ledger Review

- trial_group_id:
- trial_id:
- strategy_id:
- parameter_hash:
- data_snapshot_id:
- feature_snapshot_id:
- signal_count:
- candidate_count:
- paper_candidate_count:
- blocked_count:
- no_signal_count:
- top blocked_reason_counts:
- primary_metric:
- baseline_strategy_id:
- baseline_delta_metrics:
- selected_for_next_stage: true | false
- rejection_reasons:
- reviewer note:
```

Stop if:

- all trials are not recorded.
- `parameter_count <= 0`.
- `profitability_claimed=true`.
- `paper_ready_claimed=true`.
- `live_ready_claimed=true`.

## 6. TradeCandidate Review Template

```md
# TradeCandidate Review

- candidate_id:
- signal_id:
- trial_id:
- strategy_id:
- execution_venue:
- execution_symbol:
- real_market_symbol:
- side:
- timeframe:
- status: candidate | blocked | no_signal | hold
- rank_score:
- percentile_rank:
- tail_bucket:
- confidence:
- source_confidence:
- venue_quality_score:
- unique_contribution_score:
- index_exposure_score:
- entry_reason_codes:
- block_reasons:
- feature_snapshot_ref:
- quote_ref:
- tracking_ref:
- live_order_submitted: false
```

Checklist:

- candidate は order ではない。
- selected 理由が entry reason として説明できる。
- blocked の場合、block reason が taxonomy 化されている。
- symbol binding が崩れていない。

## 7. PaperCandidatePack Checklist

- `pack_id` がある。
- `evaluation_plan_id` がある。
- `data_snapshot_id` がある。
- `feature_snapshot_id` がある。
- selected / rejected IDs は `candidates` 内に存在する。
- top-level `blocked_candidate_ids` を期待していない。
- `selection_policy` が再現可能な粒度で書かれている。
- `profitability_claimed=false`。
- `paper_ready_claimed=false`。
- `tiny_live_ready_claimed=false`。
- `live_ready_claimed=false`。
- `live_order_submitted=false`。
- `wallet_used=false`。
- `exchange_write_used=false`。

## 8. PromotionDecision Template

```md
# PromotionDecision Review

- promotion_id:
- source_pack_id:
- reviewer:
- from_stage: strategy_lab | paper_candidate
- to_stage: paper_observation | micro_live_candidate
- decision: promote | reject | hold
- required_evidence:
- observed_evidence:
- approval_reasons:
- rejection_reasons:
- paper_ready_claimed: false
- tiny_live_ready_claimed: false
- live_ready_claimed: false
- wallet_used: false
- exchange_write_used: false
```

Rules:

- `promote` は required evidence がすべて observed にある。
- `promote` は approval reason が必要。
- `reject` / `hold` は rejection reason が必要。
- `promote` は paper observation への許可であり、live-ready ではない。

## 9. PaperIntentPreview Checklist

- `source_pack_id` がある。
- `candidate_id` がある。
- `strategy_id` がある。
- `execution_venue=trade_xyz`。
- `execution_symbol` と `real_market_symbol` がある。
- `action` は `enter | exit | reduce | skip`。
- `side` は `long | short | none`。
- `order_style` は `paper_taker | paper_maker | skip`。
- `price_reference` は `best_bid | best_ask | mid | mark | oracle`。
- `valid_until` が古すぎない。
- `requires_revalidation=true`。
- `paper_only=true`。
- `live_conversion_allowed=false`。
- `live_order_submitted=false`。
- `wallet_used=false`。
- `exchange_write_used=false`。

Stop if:

- `PaperIntentPreview` を live adapter に渡そうとしている。
- `PromotionDecision` なしで作っている。
- `valid_until` が切れているのに paper 実行しようとしている。

## 10. paper-from-intents Review Template

```md
# Paper Observation Review

- run id:
- intents_count:
- orders_count:
- fills_count:
- blocked_count:
- top block_reasons:
- expired_count:
- latest_quote_missing_count:
- broker_revalidation_blocked_count:
- observation_ledger_path:
- unexpected paper fills:
- wallet_used observed: false
- exchange_write_used observed: false
- next action: continue | hold | reject
```

Expected block reasons:

- `INTENT_EXPIRED`
- `LATEST_QUOTE_MISSING`
- `PAPER_BROKER_REVALIDATION_BLOCKED`

## 11. Reject Record

```md
# Reject Record

- candidate_id:
- strategy_id:
- rejected at stage:
- primary reason code:
- secondary reason codes:
- evidence artifact:
- could be revived if:
- source notes:
- date:
```

## 12. Continue Record

```md
# Continue Record

- candidate_id:
- strategy_id:
- continue reason:
- required next test:
- required evidence:
- risk to watch:
- max scope for next step:
- live execution allowed: no
```

## 13. Bot Boundary Checklist

- `READ_ONLY_GO` を live-ready と読んでいない。
- `bot-preview` を strategy engine として扱っていない。
- `PaperIntentPreview` を live order として扱っていない。
- `TradeCandidate` を paper/live order として扱っていない。
- wallet / secret / signing material を docs/repo に置いていない。
- public micro live CLI が無いことを理解している。
- live execution は別 gate と別 plan で扱う。
