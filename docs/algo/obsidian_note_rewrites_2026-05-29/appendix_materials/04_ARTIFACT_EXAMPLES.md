# Artifact Examples

実装や検証で出てくる成果物の形です。すべて説明用の例であり、実データではありません。

現行 Strategy Research Lab の正本は `data/research/strategy_signals.parquet` から始まる artifact chain です。旧 `data/research/signals.csv`, `DecisionContext`, `ExecutionPlan` 中心の例は legacy paper path として扱い、この文書では正本にしません。

## 1. StrategyExperimentSpec

目的: 戦略仮説、symbol binding、generator、parameter grid、evaluation plan を固定する。

```json
{
  "schema_version": "strategy_experiment_spec.v1",
  "strategy_id": "trend_pullback_xyz100_v0",
  "strategy_family": "momentum",
  "strategy_version": "v0",
  "enabled": true,
  "description": "QQQ trend pullback signal mapped to XYZ100 paper observation.",
  "symbol_bindings": [
    {
      "execution_venue": "trade_xyz",
      "execution_symbol": "XYZ100",
      "real_market_symbol": "QQQ",
      "asset_class": "basket_index",
      "country": "US",
      "currency": "USD"
    }
  ],
  "generator_id": "qqq_trend_rates_vix",
  "parameter_grid": {
    "trend_window": [20, 50],
    "min_source_confidence": [0.7, 0.8],
    "max_spread_bps": [8.0]
  },
  "evaluation_plan_id": "initial_walkforward_v1",
  "run_profile_id": "strategy_lab",
  "forbidden_claims": [
    "profitability_claimed",
    "paper_ready_claimed",
    "tiny_live_ready_claimed",
    "live_ready_claimed"
  ]
}
```

確認点:

- `XYZ100` は `QQQ` に binding されている。
- `generator_id` は registry に存在する。
- claim は `*_claimed` 名で、全部 forbidden に入っている。
- ここには quantity、wallet、live order を書かない。

## 2. StrategySignalRecord Row

目的: generator が出した signal row を canonical artifact にする。

canonical artifact:

- `data/research/strategy_signals.parquet`
- `data/research/strategy_signals.jsonl` は export
- `data/research/signals.csv` は legacy export

```json
{
  "schema_version": "strategy_signal.v1",
  "signal_id": "sig-trend-pullback-001",
  "generated_at": "2026-05-30T00:00:00+00:00",
  "strategy_id": "trend_pullback_xyz100_v0",
  "strategy_family": "momentum",
  "strategy_version": "v0",
  "trial_id": null,
  "parameter_hash": "trend20_conf070",
  "ts_signal": "2026-05-30T13:00:00+00:00",
  "timeframe": "4h",
  "execution_venue": "trade_xyz",
  "execution_symbol": "XYZ100",
  "real_market_symbol": "QQQ",
  "side": "long",
  "raw_score": 0.82,
  "rank_score": 0.90,
  "percentile_rank": 0.90,
  "tail_bucket": "top",
  "confidence": 0.78,
  "source_confidence": 0.92,
  "venue_quality_score": 0.88,
  "feature_snapshot_ref": "feature_snapshot:feature-snap-20260530",
  "quote_ref": "quote:trade_xyz:XYZ100:latest",
  "tracking_ref": "tracking:QQQ:XYZ100:latest",
  "reason_codes": ["TREND_UP", "PULLBACK_TO_SMA20", "QUALITY_OK"],
  "block_reasons": []
}
```

確認点:

- `side` は signal direction であり、order action ではない。
- `rank_score` / `percentile_rank` は 0.0 から 1.0。
- `execution_symbol` と `real_market_symbol` は別物。
- `reason_codes` と `block_reasons` は後で候補を捨てる材料になる。

## 3. EvaluationPlan

目的: 評価窓、leakage guard、cost stress、最低 trade 数、合格 metric を固定する。

```json
{
  "schema_version": "evaluation_plan.mls.v1",
  "evaluation_plan_id": "initial_walkforward_v1",
  "run_profile": "strategy_lab",
  "target_venue": "trade_xyz",
  "split_method": "purged_walk_forward",
  "label_horizon_minutes": 240,
  "purge_minutes": 240,
  "embargo_minutes": 60,
  "era_unit": "trading_day",
  "quote_data_path": "data/normalized/quotes.parquet",
  "feature_panel_path": "data/research/feature_panel.parquet",
  "tracking_data_path": "data/research/tracking.parquet",
  "cost_model_path": "configs/fee_model.trade_xyz.yaml",
  "require_tracking_gate": true,
  "require_source_confidence": true,
  "require_venue_quality": true,
  "min_trade_count": 30,
  "max_turnover": 4.0,
  "cost_stress_multiplier": 2.0,
  "slippage_stress_multiplier": 2.0,
  "primary_metric": "net_return_after_cost_stress",
  "secondary_metrics": ["max_drawdown", "trade_count", "blocked_rate"],
  "forbidden_claims": [
    "profitability_claimed",
    "paper_ready_claimed",
    "tiny_live_ready_claimed",
    "live_ready_claimed"
  ]
}
```

確認点:

- horizon / purge / embargo は positive。
- cost / slippage stress は 1.0 以上。
- `primary_metric` は採用理由であり、収益性 claim ではない。

## 4. TrialRecord

目的: 全 trial を append-only ledger に残す。

artifact:

- `data/research/trial_ledger.jsonl`

```json
{
  "schema_version": "trial_record.v1",
  "trial_id": "trial-trend-pullback-001",
  "trial_group_id": "trend-pullback-grid-20260530",
  "trial_index": 0,
  "strategy_id": "trend_pullback_xyz100_v0",
  "strategy_family": "momentum",
  "strategy_version": "v0",
  "evaluation_plan_id": "initial_walkforward_v1",
  "data_snapshot_id": "data-snap-20260530",
  "feature_snapshot_id": "feature-snap-20260530",
  "parameter_hash": "trend20_conf070",
  "parameter_count": 3,
  "parameter_space_hash": "grid-v0",
  "random_seed": null,
  "git_sha": null,
  "signal_count": 48,
  "candidate_count": 12,
  "paper_candidate_count": 2,
  "executed_count": 0,
  "blocked_count": 36,
  "no_signal_count": 0,
  "blocked_reason_counts": {
    "LOW_SOURCE_CONFIDENCE": 10,
    "VENUE_QUALITY_LOW": 8,
    "REGIME_NOT_TREND": 18
  },
  "metrics": {
    "net_return_after_cost_stress": 0.018,
    "max_drawdown": -0.042,
    "trade_count": 42
  },
  "baseline_strategy_id": "close_above_sma20_v0",
  "baseline_delta_metrics": {
    "net_return_after_cost_stress": 0.006,
    "max_drawdown": 0.015
  },
  "selected_for_next_stage": true,
  "rejection_reasons": [],
  "profitability_claimed": false,
  "paper_ready_claimed": false,
  "tiny_live_ready_claimed": false,
  "live_ready_claimed": false
}
```

確認点:

- `selected_for_next_stage=true` は paper candidate へ進めるだけ。
- `executed_count=0` は Strategy Lab 評価中なら自然。
- claim flags はすべて false。

## 5. TradeCandidate

目的: paper candidate pack に入れる売買候補。まだ order ではない。

```json
{
  "schema_version": "trade_candidate.v1",
  "candidate_id": "candidate-trial-trend-pullback-001",
  "generated_at": "2026-05-30T00:05:00+00:00",
  "signal_id": "sig-trend-pullback-001",
  "strategy_id": "trend_pullback_xyz100_v0",
  "trial_id": "trial-trend-pullback-001",
  "execution_venue": "trade_xyz",
  "execution_symbol": "XYZ100",
  "real_market_symbol": "QQQ",
  "side": "long",
  "timeframe": "4h",
  "status": "candidate",
  "raw_score": 0.82,
  "rank_score": 0.90,
  "percentile_rank": 0.90,
  "tail_bucket": "top",
  "confidence": 0.78,
  "unique_contribution_score": 0.35,
  "index_exposure_score": 0.65,
  "entry_reason_codes": ["TRIAL_SELECTED", "TOP_TAIL_BUCKET"],
  "block_reasons": [],
  "feature_snapshot_ref": "feature-snap-20260530",
  "quote_ref": "quote:trade_xyz:XYZ100:latest",
  "tracking_ref": "tracking:QQQ:XYZ100:latest",
  "live_order_submitted": false
}
```

確認点:

- `TradeCandidate` は order ではない。
- `live_order_submitted=false`。
- `entry_reason_codes` が候補化理由を説明する。

## 6. PaperCandidatePack

目的: selected / rejected candidates を束ね、paper observation へ進める前の判断材料にする。

artifact:

- `data/research/paper_candidate_pack.json`

```json
{
  "schema_version": "paper_candidate_pack.v1",
  "pack_id": "paper-pack-trend-pullback-20260530",
  "generated_at": "2026-05-30T00:10:00+00:00",
  "evaluation_plan_id": "initial_walkforward_v1",
  "data_snapshot_id": "data-snap-20260530",
  "feature_snapshot_id": "feature-snap-20260530",
  "trial_group_id": "trend-pullback-grid-20260530",
  "candidates": ["<TradeCandidate objects>"],
  "selected_candidate_ids": ["candidate-trial-trend-pullback-001"],
  "rejected_candidate_ids": ["candidate-trial-trend-pullback-002"],
  "selection_policy": {
    "tail_bucket": "top",
    "min_confidence": 0.75,
    "requires_no_block_reasons": true
  },
  "reason_codes": ["SELECT_TOP_RANKED_CANDIDATE"],
  "block_reasons": [],
  "profitability_claimed": false,
  "paper_ready_claimed": false,
  "tiny_live_ready_claimed": false,
  "live_ready_claimed": false,
  "live_order_submitted": false,
  "wallet_used": false,
  "exchange_write_used": false
}
```

確認点:

- `selected_candidate_ids` は `candidates` 内のIDである。
- top-level `blocked_candidate_ids` は現行 code にはない。
- pack は paper-ready 証明ではない。

## 7. PromotionDecision

目的: `PaperIntentPreview` 生成前の人間判断 artifact。

artifact:

- `data/research/promotion_decision.json`

```json
{
  "schema_version": "promotion_decision.v1",
  "promotion_id": "promotion-trend-pullback-20260530",
  "generated_at": "2026-05-30T00:15:00+00:00",
  "source_pack_id": "paper-pack-trend-pullback-20260530",
  "reviewer": "operator",
  "from_stage": "strategy_lab",
  "to_stage": "paper_observation",
  "decision": "hold",
  "required_evidence": ["trial_ledger", "paper_candidate_pack"],
  "observed_evidence": ["trial_ledger", "paper_candidate_pack"],
  "approval_reasons": [],
  "rejection_reasons": ["manual_review_required_before_promote"],
  "paper_ready_claimed": false,
  "tiny_live_ready_claimed": false,
  "live_ready_claimed": false,
  "wallet_used": false,
  "exchange_write_used": false
}
```

確認点:

- `hold` / `reject` は `rejection_reasons` が必要。
- `promote` には observed evidence と approval reason が必要。
- `promote` は paper observation への許可で、live-ready ではない。

## 8. PaperIntentPreview

目的: paper runner へ渡す仮注文意図。live order ではない。

artifact:

- `data/bot/paper_intent_preview.json`

```json
[
  {
    "schema_version": "paper_intent_preview.v1",
    "intent_id": "intent-candidate-trial-trend-pullback-001",
    "generated_at": "2026-05-30T00:20:00+00:00",
    "valid_until": "2026-05-30T00:35:00+00:00",
    "source_pack_id": "paper-pack-trend-pullback-20260530",
    "candidate_id": "candidate-trial-trend-pullback-001",
    "strategy_id": "trend_pullback_xyz100_v0",
    "execution_venue": "trade_xyz",
    "execution_symbol": "XYZ100",
    "real_market_symbol": "QQQ",
    "action": "enter",
    "side": "long",
    "order_style": "paper_taker",
    "price_reference": "mark",
    "notional_usd": 1000.0,
    "quantity": 1.0,
    "source_quote_ts": null,
    "source_tracking_ts": null,
    "source_feature_ts": "2026-05-30T00:00:00+00:00",
    "source_phase_gate_run_id": null,
    "requires_revalidation": true,
    "paper_only": true,
    "live_conversion_allowed": false,
    "live_order_submitted": false,
    "wallet_used": false,
    "exchange_write_used": false
  }
]
```

確認点:

- `requires_revalidation=true`。
- `paper_only=true`。
- `live_conversion_allowed=false`。
- `wallet_used=false`, `exchange_write_used=false`。

## 9. Paper Observation Ledger

目的: `paper-from-intents` の再検証結果を残す。

artifact:

- `data/paper/paper_observation_ledger.jsonl`

```jsonl
{"intent_id":"intent-candidate-trial-trend-pullback-001","status":"paper_filled","order_id":"paper-order-001","fill_id":"paper-fill-001","live_order_submitted":false,"wallet_used":false,"exchange_write_used":false}
{"intent_id":"intent-candidate-trial-trend-pullback-002","status":"blocked","block_reasons":["INTENT_EXPIRED"],"live_order_submitted":false,"wallet_used":false,"exchange_write_used":false}
```

確認点:

- blocked は失敗とは限らない。再検証で止まるのは期待される安全動作。
- observation ledger に wallet / exchange write が出てはいけない。
