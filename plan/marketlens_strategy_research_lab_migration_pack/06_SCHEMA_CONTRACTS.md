# 06 Schema Contracts

この文書は主要スキーマの契約を定義する。完全なJSON Schemaは `templates/` にsketchとして置く。

## DataSnapshotManifest

```python
class DataSnapshotManifest(BaseModel):
    schema_version: Literal["data_snapshot_manifest.v1"]
    data_snapshot_id: str
    generated_at: datetime
    quote_data_path: str
    quote_data_sha256: str | None
    feature_panel_path: str
    feature_panel_sha256: str | None
    tracking_data_path: str | None
    tracking_data_sha256: str | None
    phase_gate_summary_path: str | None
    phase_gate_decision: str | None
    symbols: list[str]
    venues: list[str]
    min_ts: datetime | None
    max_ts: datetime | None
    data_quality_summary: dict[str, Any]
```

## FeatureSnapshotManifest

```python
class FeatureSnapshotManifest(BaseModel):
    schema_version: Literal["feature_snapshot_manifest.v1"]
    feature_snapshot_id: str
    generated_at: datetime
    input_data_snapshot_id: str
    feature_panel_path: str
    feature_panel_sha256: str | None
    feature_version: str
    feature_build_config_hash: str
    feature_cutoff_policy: str
    max_feature_source_ts: datetime | None
    leakage_checks: dict[str, Any]
    missing_rate_by_feature: dict[str, float]
```

## StrategyExperimentSpec

```python
class StrategyExperimentSpec(BaseModel):
    schema_version: Literal["strategy_experiment_spec.v1"]
    strategy_id: str
    strategy_family: str
    strategy_version: str
    enabled: bool
    description: str | None
    symbol_bindings: list[SymbolBinding]
    generator_id: str
    parameter_grid: dict[str, list[Any]]
    evaluation_plan_id: str
    run_profile_id: str
    forbidden_claims: list[str]
```

## StrategySignalRecord

```python
class StrategySignalRecord(BaseModel):
    schema_version: Literal["strategy_signal.v1"]
    signal_id: str
    generated_at: datetime
    strategy_id: str
    strategy_family: str
    strategy_version: str
    trial_id: str | None
    parameter_hash: str | None
    ts_signal: datetime
    timeframe: str
    execution_venue: Literal["trade_xyz"]
    execution_symbol: str
    real_market_symbol: str
    side: Literal["long", "short", "none"]
    raw_score: float | None
    rank_score: float | None
    percentile_rank: float | None
    tail_bucket: Literal["top", "middle", "bottom", "none"]
    confidence: float
    source_confidence: float | None
    venue_quality_score: float | None
    feature_snapshot_ref: str | None
    quote_ref: str | None
    tracking_ref: str | None
    reason_codes: list[str]
    block_reasons: list[str]
```

## EvaluationPlan

```python
class EvaluationPlan(BaseModel):
    schema_version: Literal["evaluation_plan.mls.v1"]
    evaluation_plan_id: str
    run_profile: Literal["strategy_lab", "walkforward_research", "paper_candidate"]
    target_venue: Literal["trade_xyz"]
    split_method: Literal["single_window", "walk_forward", "purged_walk_forward"]
    label_horizon_minutes: int
    purge_minutes: int
    embargo_minutes: int
    era_unit: Literal["session", "trading_day", "week", "month"]
    quote_data_path: str
    feature_panel_path: str
    tracking_data_path: str | None
    cost_model_path: str
    require_tracking_gate: bool = True
    require_source_confidence: bool = True
    require_venue_quality: bool = True
    min_trade_count: int
    max_turnover: float | None = None
    cost_stress_multiplier: float = 2.0
    slippage_stress_multiplier: float = 2.0
    primary_metric: str
    secondary_metrics: list[str]
    forbidden_claims: list[str]
```

## TrialRecord

```python
class TrialRecord(BaseModel):
    schema_version: Literal["trial_record.v1"]
    trial_id: str
    trial_group_id: str
    trial_index: int
    strategy_id: str
    strategy_family: str
    strategy_version: str
    evaluation_plan_id: str
    data_snapshot_id: str
    feature_snapshot_id: str | None
    parameter_hash: str
    parameter_count: int
    parameter_space_hash: str | None
    random_seed: int | None
    git_sha: str | None
    signal_count: int
    candidate_count: int
    paper_candidate_count: int
    executed_count: int
    blocked_count: int
    no_signal_count: int
    blocked_reason_counts: dict[str, int]
    metrics: dict[str, Any]
    baseline_strategy_id: str | None
    baseline_delta_metrics: dict[str, Any]
    selected_for_next_stage: bool = False
    rejection_reasons: list[str]
    profitability_claimed: bool = False
    paper_ready_claimed: bool = False
    tiny_live_ready_claimed: bool = False
    live_ready_claimed: bool = False
```

## TradeCandidate

```python
class TradeCandidate(BaseModel):
    schema_version: Literal["trade_candidate.v1"]
    candidate_id: str
    generated_at: datetime
    signal_id: str | None
    strategy_id: str
    trial_id: str | None
    execution_venue: Literal["trade_xyz"]
    execution_symbol: str
    real_market_symbol: str
    side: Literal["long", "short", "none"]
    timeframe: str
    status: Literal["candidate", "blocked", "no_signal", "hold"]
    raw_score: float | None
    rank_score: float | None
    percentile_rank: float | None
    tail_bucket: Literal["top", "middle", "bottom", "none"]
    confidence: float
    unique_contribution_score: float | None = None
    index_exposure_score: float | None = None
    entry_reason_codes: list[str]
    block_reasons: list[str]
    feature_snapshot_ref: str | None
    quote_ref: str | None
    tracking_ref: str | None
    live_order_submitted: bool = False
```

## PaperCandidatePack

```python
class PaperCandidatePack(BaseModel):
    schema_version: Literal["paper_candidate_pack.v1"]
    pack_id: str
    generated_at: datetime
    evaluation_plan_id: str
    data_snapshot_id: str
    feature_snapshot_id: str | None
    trial_group_id: str | None
    candidates: list[TradeCandidate]
    selected_candidate_ids: list[str]
    rejected_candidate_ids: list[str]
    selection_policy: dict[str, Any]
    reason_codes: list[str]
    block_reasons: list[str]
    profitability_claimed: bool = False
    paper_ready_claimed: bool = False
    tiny_live_ready_claimed: bool = False
    live_ready_claimed: bool = False
    live_order_submitted: bool = False
    wallet_used: bool = False
    exchange_write_used: bool = False
```

## PromotionDecision

```python
class PromotionDecision(BaseModel):
    schema_version: Literal["promotion_decision.v1"]
    promotion_id: str
    generated_at: datetime
    source_pack_id: str
    reviewer: str | None
    from_stage: Literal["strategy_lab", "paper_candidate"]
    to_stage: Literal["paper_observation", "micro_live_candidate"]
    decision: Literal["promote", "reject", "hold"]
    required_evidence: list[str]
    observed_evidence: list[str]
    approval_reasons: list[str]
    rejection_reasons: list[str]
    paper_ready_claimed: bool = False
    tiny_live_ready_claimed: bool = False
    live_ready_claimed: bool = False
    wallet_used: bool = False
    exchange_write_used: bool = False
```

## PaperIntentPreview

```python
class PaperIntentPreview(BaseModel):
    schema_version: Literal["paper_intent_preview.v1"]
    intent_id: str
    generated_at: datetime
    valid_until: datetime | None
    source_pack_id: str
    candidate_id: str
    strategy_id: str
    execution_venue: Literal["trade_xyz"]
    execution_symbol: str
    real_market_symbol: str
    action: Literal["enter", "exit", "reduce", "skip"]
    side: Literal["long", "short", "none"]
    order_style: Literal["paper_taker", "paper_maker", "skip"]
    price_reference: Literal["best_bid", "best_ask", "mid", "mark", "oracle"]
    notional_usd: float | None
    quantity: float | None
    source_quote_ts: datetime | None
    source_tracking_ts: datetime | None
    source_feature_ts: datetime | None
    source_phase_gate_run_id: str | None
    requires_revalidation: bool = True
    paper_only: bool = True
    live_conversion_allowed: bool = False
    live_order_submitted: bool = False
    wallet_used: bool = False
    exchange_write_used: bool = False
```
