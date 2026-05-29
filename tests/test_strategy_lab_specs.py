from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from sis.research.strategy_lab.specs import (
    StrategyExperimentSpec,
    StrategySignalRecord,
    SymbolBinding,
)


def test_symbol_binding_keeps_execution_and_real_market_symbols_separate() -> None:
    binding = SymbolBinding(
        execution_venue="trade_xyz",
        execution_symbol="XYZ100",
        real_market_symbol="QQQ",
        asset_class="basket_index",
    )

    assert binding.execution_symbol == "XYZ100"
    assert binding.real_market_symbol == "QQQ"
    assert binding.currency == "USD"


def test_symbol_binding_requires_explicit_proxy_for_xyz100() -> None:
    with pytest.raises(ValidationError, match="XYZ100"):
        SymbolBinding(
            execution_venue="trade_xyz",
            execution_symbol="XYZ100",
            real_market_symbol="XYZ100",
            asset_class="basket_index",
        )


def test_strategy_experiment_spec_rejects_live_claims() -> None:
    with pytest.raises(ValidationError, match="live_ready_claim"):
        StrategyExperimentSpec(
            schema_version="strategy_experiment_spec.v1",
            strategy_id="equity_index_momentum_v0",
            strategy_family="momentum",
            strategy_version="v0",
            enabled=True,
            description=None,
            symbol_bindings=[
                SymbolBinding(
                    execution_venue="trade_xyz",
                    execution_symbol="SP500",
                    real_market_symbol="SPY",
                    asset_class="index",
                )
            ],
            generator_id="qqq_trend_rates_vix",
            parameter_grid={"min_source_confidence": [0.7]},
            evaluation_plan_id="initial_single_window_v1",
            run_profile_id="strategy_lab",
            forbidden_claims=["profitability_claim", "live_ready_claim"],
        )


def test_strategy_signal_record_requires_symbol_binding_fields() -> None:
    signal = StrategySignalRecord(
        schema_version="strategy_signal.v1",
        signal_id="sig-001",
        generated_at=datetime.now(timezone.utc),
        strategy_id="equity_index_momentum_v0",
        strategy_family="momentum",
        strategy_version="v0",
        trial_id=None,
        parameter_hash=None,
        ts_signal=datetime.now(timezone.utc),
        timeframe="4h",
        execution_venue="trade_xyz",
        execution_symbol="XYZ100",
        real_market_symbol="QQQ",
        side="long",
        raw_score=1.2,
        rank_score=0.95,
        percentile_rank=0.95,
        tail_bucket="top",
        confidence=0.8,
        source_confidence=0.75,
        venue_quality_score=0.82,
        feature_snapshot_ref="feature_snapshot:demo",
        quote_ref="quote:demo",
        tracking_ref="tracking:demo",
        reason_codes=["close_above_sma20"],
        block_reasons=[],
    )

    assert signal.execution_symbol == "XYZ100"
    assert signal.real_market_symbol == "QQQ"
