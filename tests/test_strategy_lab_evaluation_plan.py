from __future__ import annotations

import pytest
from pydantic import ValidationError

from sis.research.strategy_lab.evaluation_plan import EvaluationPlan


def test_evaluation_plan_requires_purge_and_embargo() -> None:
    with pytest.raises(ValidationError, match="purge_minutes"):
        EvaluationPlan(
            schema_version="evaluation_plan.mls.v1",
            evaluation_plan_id="initial_walkforward",
            run_profile="strategy_lab",
            target_venue="trade_xyz",
            split_method="purged_walk_forward",
            label_horizon_minutes=240,
            purge_minutes=0,
            embargo_minutes=60,
            era_unit="trading_day",
            quote_data_path="data/normalized/quotes.parquet",
            feature_panel_path="data/research/feature_panel.parquet",
            tracking_data_path=None,
            cost_model_path="configs/fee_model.trade_xyz.yaml",
            min_trade_count=20,
            primary_metric="per_era_mean_return_after_cost",
            secondary_metrics=["sharpe", "max_drawdown"],
            forbidden_claims=["profitability_claimed", "paper_ready_claimed", "live_ready_claimed"],
        )


def test_evaluation_plan_accepts_strategy_lab_research_profile() -> None:
    plan = EvaluationPlan(
        schema_version="evaluation_plan.mls.v1",
        evaluation_plan_id="initial_walkforward",
        run_profile="strategy_lab",
        target_venue="trade_xyz",
        split_method="purged_walk_forward",
        label_horizon_minutes=240,
        purge_minutes=240,
        embargo_minutes=60,
        era_unit="trading_day",
        quote_data_path="data/normalized/quotes.parquet",
        feature_panel_path="data/research/feature_panel.parquet",
        tracking_data_path="data/research/tracking_records.parquet",
        cost_model_path="configs/fee_model.trade_xyz.yaml",
        min_trade_count=20,
        primary_metric="per_era_mean_return_after_cost",
        secondary_metrics=["sharpe", "max_drawdown"],
        forbidden_claims=[
            "profitability_claimed",
            "paper_ready_claimed",
            "tiny_live_ready_claimed",
            "live_ready_claimed",
        ],
    )

    assert plan.require_tracking_gate is True
    assert plan.cost_stress_multiplier == 2.0
