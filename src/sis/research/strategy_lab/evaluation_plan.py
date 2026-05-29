from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, model_validator

from sis.research.strategy_lab.run_profile import DEFAULT_FORBIDDEN_CLAIMS


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

    @model_validator(mode="after")
    def validate_plan(self) -> EvaluationPlan:
        if not self.evaluation_plan_id.strip():
            raise ValueError("evaluation_plan_id must be non-empty")
        if self.label_horizon_minutes <= 0:
            raise ValueError("label_horizon_minutes must be positive")
        if self.purge_minutes <= 0:
            raise ValueError("purge_minutes must be positive")
        if self.embargo_minutes <= 0:
            raise ValueError("embargo_minutes must be positive")
        if self.min_trade_count <= 0:
            raise ValueError("min_trade_count must be positive")
        if self.cost_stress_multiplier < 1.0:
            raise ValueError("cost_stress_multiplier must be >= 1")
        if self.slippage_stress_multiplier < 1.0:
            raise ValueError("slippage_stress_multiplier must be >= 1")
        missing = set(DEFAULT_FORBIDDEN_CLAIMS).difference(self.forbidden_claims)
        if missing:
            raise ValueError(f"forbidden_claims missing: {sorted(missing)}")
        return self
