from __future__ import annotations

from types import SimpleNamespace

import polars as pl
import pytest

from sis.research.strategy_lab.authoring.contracts.base import StrategyAuthoringValidationError
from sis.research.strategy_lab.authoring.contracts.derived import DerivedFeature
from sis.research.strategy_lab.authoring.derived_bands_channels import (
    BANDS_CHANNEL_DERIVED_OPS,
    bands_channel_expression,
)
from sis.research.strategy_lab.authoring.derived_cross_sectional import (
    CROSS_SECTIONAL_DERIVED_OPS,
    cross_sectional_expression,
)
from sis.research.strategy_lab.authoring.derived_drawdown import (
    DRAWDOWN_DERIVED_OPS,
    drawdown_expression,
)
from sis.research.strategy_lab.authoring.derived_execution_costs import (
    EXECUTION_COST_DERIVED_OPS,
    execution_cost_expression,
)
from sis.research.strategy_lab.authoring.derived_external_signals import (
    EXTERNAL_SIGNAL_DERIVED_OPS,
    external_signal_expression,
)
from sis.research.strategy_lab.authoring.derived_features import (
    apply_derived_features,
    derived_expression,
)
from sis.research.strategy_lab.authoring.derived_liquidity import (
    LIQUIDITY_DERIVED_OPS,
    liquidity_expression,
)
from sis.research.strategy_lab.authoring.derived_quality import (
    QUALITY_DERIVED_OPS,
    quality_expression,
)
from sis.research.strategy_lab.authoring.derived_trend_indicators import (
    TREND_INDICATOR_DERIVED_OPS,
    trend_indicator_expression,
)
from sis.research.strategy_lab.authoring.derived_volume_indicators import (
    VOLUME_INDICATOR_DERIVED_OPS,
    volume_indicator_expression,
)


def test_apply_derived_features_computes_representative_ops() -> None:
    frame = pl.DataFrame(
        {
            "canonical_symbol": ["QQQ", "QQQ", "SPY", "SPY"],
            "ts": [1, 2, 1, 2],
            "close": [100.0, 110.0, 50.0, 55.0],
            "ret": [0.01, 0.02, 0.03, -0.01],
            "score": [3.0, 2.0, 1.0, 4.0],
        }
    )
    spec = SimpleNamespace(
        rules=SimpleNamespace(
            derived_features=[
                DerivedFeature(
                    name="rolling_return_1",
                    op="rolling_return",
                    columns=["close"],
                    window=1,
                    fill_null=0,
                ),
                DerivedFeature(
                    name="realized_var_2",
                    op="realized_variance",
                    columns=["ret"],
                    window=2,
                ),
                DerivedFeature(
                    name="score_rank",
                    op="cross_sectional_rank",
                    columns=["score"],
                ),
            ]
        )
    )

    result = apply_derived_features(frame, spec).sort(["canonical_symbol", "ts"])

    assert result.get_column("rolling_return_1").to_list() == pytest.approx([0.0, 0.1, 0.0, 0.1])
    assert result.get_column("realized_var_2").to_list() == pytest.approx(
        [0.0001, 0.00025, 0.0009, 0.0005]
    )
    assert result.sort(["ts", "canonical_symbol"]).get_column("score_rank").to_list() == [
        1.0,
        0.0,
        0.0,
        1.0,
    ]


def test_derived_expression_uses_null_for_zero_denominator() -> None:
    frame = pl.DataFrame({"canonical_symbol": ["QQQ"], "ts": [1], "left": [10.0], "right": [0.0]})
    feature = DerivedFeature(name="ratio", op="ratio", columns=["left", "right"])

    result = frame.with_columns(derived_expression(feature))

    assert result.get_column("ratio").to_list() == [None]


def test_derived_expression_rejects_unsupported_constructed_op() -> None:
    feature = DerivedFeature.model_construct(
        name="unsupported",
        op="unsupported",
        columns=["left"],
        value=None,
        window=None,
        fill_null=None,
    )

    with pytest.raises(StrategyAuthoringValidationError, match="Unsupported derived feature op"):
        derived_expression(feature)


def test_cross_sectional_expression_ranks_and_standardizes_by_timestamp() -> None:
    frame = pl.DataFrame(
        {
            "ts": [1, 1, 1],
            "canonical_symbol": ["AAA", "BBB", "CCC"],
            "score": [3.0, 1.0, 2.0],
        }
    )

    result = frame.with_columns(
        [
            cross_sectional_expression(
                DerivedFeature(name="rank", op="cross_sectional_rank", columns=["score"])
            ).alias("rank"),
            cross_sectional_expression(
                DerivedFeature(name="z", op="cross_sectional_zscore", columns=["score"])
            ).alias("z"),
            cross_sectional_expression(
                DerivedFeature(name="demean", op="cross_sectional_demean", columns=["score"])
            ).alias("demean"),
        ]
    ).sort("canonical_symbol")

    assert CROSS_SECTIONAL_DERIVED_OPS == {
        "cross_sectional_rank",
        "cross_sectional_zscore",
        "cross_sectional_demean",
        "group_cross_sectional_rank",
        "group_cross_sectional_zscore",
        "group_cross_sectional_demean",
    }
    assert result.get_column("rank").to_list() == pytest.approx([1.0, 0.0, 0.5])
    assert result.get_column("z").to_list() == pytest.approx([1.0, -1.0, 0.0])
    assert result.get_column("demean").to_list() == pytest.approx([1.0, -1.0, 0.0])


def test_cross_sectional_expression_handles_group_variants() -> None:
    frame = pl.DataFrame(
        {
            "ts": [1, 1, 1],
            "canonical_symbol": ["AAA", "BBB", "CCC"],
            "group": ["tech", "tech", "health"],
            "score": [3.0, 1.0, 2.0],
        }
    )

    result = frame.with_columns(
        [
            cross_sectional_expression(
                DerivedFeature(
                    name="rank",
                    op="group_cross_sectional_rank",
                    columns=["score", "group"],
                )
            ).alias("rank"),
            cross_sectional_expression(
                DerivedFeature(
                    name="z",
                    op="group_cross_sectional_zscore",
                    columns=["score", "group"],
                )
            ).alias("z"),
            cross_sectional_expression(
                DerivedFeature(
                    name="demean",
                    op="group_cross_sectional_demean",
                    columns=["score", "group"],
                )
            ).alias("demean"),
        ]
    ).sort("canonical_symbol")

    assert result.get_column("rank").to_list() == pytest.approx([1.0, 0.0, 1.0])
    z_values = result.get_column("z").to_list()
    assert z_values[:2] == pytest.approx([0.7071067812, -0.7071067812])
    assert z_values[2] is None
    assert result.get_column("demean").to_list() == pytest.approx([1.0, -1.0, 0.0])


def test_execution_cost_expression_computes_execution_constraint_ops() -> None:
    frame = pl.DataFrame(
        {
            "ahead": [2.0, 0.0],
            "behind": [6.0, 0.0],
            "latency_ms": [4.0, 2.0],
            "maker_fee": [1.0, 2.5],
            "taker_fee": [3.0, 2.0],
            "borrow_rate": [0.02, 0.01],
            "hold_years": [0.5, 2.0],
            "borrow_available": [40.0, 3.0],
            "borrow_needed": [80.0, 0.0],
            "tax_rate": [0.2, 0.3],
            "gain": [0.1, -0.2],
            "target_weight": [0.6, -0.25],
            "current_weight": [0.4, 0.1],
        }
    )

    result = frame.with_columns(
        [
            execution_cost_expression(
                DerivedFeature(
                    name="queue",
                    op="queue_position_score",
                    columns=["ahead", "behind"],
                )
            ).alias("queue"),
            execution_cost_expression(
                DerivedFeature(
                    name="latency",
                    op="latency_penalty_bps",
                    columns=["latency_ms"],
                    value=0.5,
                )
            ).alias("latency"),
            execution_cost_expression(
                DerivedFeature(
                    name="fee_edge",
                    op="maker_taker_fee_edge_bps",
                    columns=["maker_fee", "taker_fee"],
                )
            ).alias("fee_edge"),
            execution_cost_expression(
                DerivedFeature(
                    name="borrow_cost",
                    op="borrow_cost_bps",
                    columns=["borrow_rate", "hold_years"],
                )
            ).alias("borrow_cost"),
            execution_cost_expression(
                DerivedFeature(
                    name="borrow_availability",
                    op="borrow_availability_ratio",
                    columns=["borrow_available", "borrow_needed"],
                )
            ).alias("borrow_availability"),
            execution_cost_expression(
                DerivedFeature(
                    name="tax_drag",
                    op="tax_drag_bps",
                    columns=["tax_rate", "gain"],
                )
            ).alias("tax_drag"),
            execution_cost_expression(
                DerivedFeature(
                    name="rebalance",
                    op="rebalance_drift",
                    columns=["target_weight", "current_weight"],
                )
            ).alias("rebalance"),
        ]
    )

    assert EXECUTION_COST_DERIVED_OPS == {
        "queue_position_score",
        "latency_penalty_bps",
        "maker_taker_fee_edge_bps",
        "borrow_cost_bps",
        "borrow_availability_ratio",
        "tax_drag_bps",
        "rebalance_drift",
    }
    assert result.get_column("queue").to_list() == pytest.approx([0.75, None])
    assert result.get_column("latency").to_list() == pytest.approx([2.0, 1.0])
    assert result.get_column("fee_edge").to_list() == pytest.approx([2.0, -0.5])
    assert result.get_column("borrow_cost").to_list() == pytest.approx([100.0, 200.0])
    assert result.get_column("borrow_availability").to_list() == pytest.approx([0.5, None])
    assert result.get_column("tax_drag").to_list() == pytest.approx([200.0, -600.0])
    assert result.get_column("rebalance").to_list() == pytest.approx([0.2, 0.35])


def test_liquidity_expression_computes_flow_carry_and_vol_ops() -> None:
    frame = pl.DataFrame(
        {
            "bid_size": [1300.0, 0.0],
            "ask_size": [700.0, 0.0],
            "bid_depth_usd": [2_000_000.0, 10.0],
            "ask_depth_usd": [1_000_000.0, 0.0],
            "best_bid": [99.95, 100.0],
            "best_ask": [100.05, 101.0],
            "depth_1pct_usd": [2_000_000.0, 0.0],
            "research_return": [0.004, -0.001],
            "funding_rate": [0.00005, 0.0001],
            "implied_vol": [0.32, 0.20],
            "realized_vol": [0.24, 0.25],
            "put_iv": [0.35, 0.21],
            "call_iv": [0.29, 0.23],
        }
    )

    result = frame.with_columns(
        [
            liquidity_expression(
                DerivedFeature(
                    name="flow",
                    op="order_flow_imbalance",
                    columns=["bid_size", "ask_size"],
                )
            ).alias("flow"),
            liquidity_expression(
                DerivedFeature(
                    name="depth_ratio",
                    op="liquidity_depth_ratio",
                    columns=["bid_depth_usd", "ask_depth_usd"],
                )
            ).alias("depth_ratio"),
            liquidity_expression(
                DerivedFeature(
                    name="spread",
                    op="spread_bps",
                    columns=["best_bid", "best_ask"],
                )
            ).alias("spread"),
            liquidity_expression(
                DerivedFeature(name="funding", op="funding_bps", columns=["funding_rate"])
            ).alias("funding"),
            liquidity_expression(
                DerivedFeature(
                    name="carry",
                    op="carry_adjusted_return",
                    columns=["research_return", "funding_rate"],
                )
            ).alias("carry"),
            liquidity_expression(
                DerivedFeature(
                    name="vrp",
                    op="vol_risk_premium",
                    columns=["implied_vol", "realized_vol"],
                )
            ).alias("vrp"),
            liquidity_expression(
                DerivedFeature(name="skew", op="put_call_skew", columns=["put_iv", "call_iv"])
            ).alias("skew"),
            liquidity_expression(
                DerivedFeature(
                    name="stress",
                    op="liquidity_stress",
                    columns=["best_bid", "best_ask", "depth_1pct_usd"],
                )
            ).alias("stress"),
        ]
    )

    assert LIQUIDITY_DERIVED_OPS == {
        "order_flow_imbalance",
        "liquidity_depth_ratio",
        "spread_bps",
        "funding_bps",
        "carry_adjusted_return",
        "vol_risk_premium",
        "put_call_skew",
        "liquidity_stress",
    }
    assert result.get_column("flow").to_list() == pytest.approx([0.3, None])
    assert result.get_column("depth_ratio").to_list() == pytest.approx([2.0, None])
    assert result.get_column("spread").to_list() == pytest.approx([10.0, 99.5024875622])
    assert result.get_column("funding").to_list() == pytest.approx([0.5, 1.0])
    assert result.get_column("carry").to_list() == pytest.approx([0.00395, -0.0011])
    assert result.get_column("vrp").to_list() == pytest.approx([0.08, -0.05])
    assert result.get_column("skew").to_list() == pytest.approx([0.06, -0.02])
    assert result.get_column("stress").to_list() == pytest.approx([0.000005, None])


def test_quality_expression_computes_quality_ensemble_and_capacity_ops() -> None:
    frame = pl.DataFrame(
        {
            "feature_age_minutes": [5.0, 30.0, 40.0],
            "source_confidence": [0.9, 0.7, 0.5],
            "venue_quality_score": [0.8, 0.6, 0.4],
            "lineage_completeness": [1.0, 0.5, 0.3],
            "trend_vote": [1.0, 0.0, 1.0],
            "mean_reversion_vote": [1.0, 1.0, 0.0],
            "event_vote": [0.0, 0.0, 0.0],
            "current_regime_score": [0.7, 0.4, 0.1],
            "previous_regime_score": [0.3, 0.5, 0.1],
            "trade_notional_usd": [100_000.0, 50_000.0, 10.0],
            "average_daily_volume_usd": [2_000_000.0, 0.0, 20.0],
            "target_notional_usd": [200_000.0, 50_000.0, 10.0],
            "strategy_capacity_usd": [1_000_000.0, 0.0, 20.0],
            "average_pair_corr": [0.4, 0.8, 0.0],
            "gross_exposure": [1.2, 0.5, 0.0],
        }
    )

    result = frame.with_columns(
        [
            quality_expression(
                DerivedFeature(
                    name="freshness",
                    op="freshness_score",
                    columns=["feature_age_minutes"],
                    value=30.0,
                )
            ).alias("freshness"),
            quality_expression(
                DerivedFeature(
                    name="stale",
                    op="staleness_bps",
                    columns=["feature_age_minutes"],
                    value=0.2,
                )
            ).alias("stale"),
            quality_expression(
                DerivedFeature(
                    name="quality",
                    op="data_quality_blend",
                    columns=["source_confidence", "venue_quality_score", "lineage_completeness"],
                )
            ).alias("quality"),
            quality_expression(
                DerivedFeature(
                    name="votes",
                    op="ensemble_vote_count",
                    columns=["trend_vote", "mean_reversion_vote", "event_vote"],
                )
            ).alias("votes"),
            quality_expression(
                DerivedFeature(
                    name="vote_ratio",
                    op="ensemble_vote_ratio",
                    columns=["trend_vote", "mean_reversion_vote", "event_vote"],
                )
            ).alias("vote_ratio"),
            quality_expression(
                DerivedFeature(
                    name="regime",
                    op="regime_transition_score",
                    columns=["current_regime_score", "previous_regime_score"],
                )
            ).alias("regime"),
            quality_expression(
                DerivedFeature(
                    name="turnover",
                    op="turnover_pressure",
                    columns=["trade_notional_usd", "average_daily_volume_usd"],
                )
            ).alias("turnover"),
            quality_expression(
                DerivedFeature(
                    name="capacity",
                    op="capacity_usage_ratio",
                    columns=["target_notional_usd", "strategy_capacity_usd"],
                )
            ).alias("capacity"),
            quality_expression(
                DerivedFeature(
                    name="crowding",
                    op="correlation_crowding_score",
                    columns=["average_pair_corr", "gross_exposure"],
                )
            ).alias("crowding"),
        ]
    )

    assert QUALITY_DERIVED_OPS == {
        "freshness_score",
        "staleness_bps",
        "data_quality_blend",
        "ensemble_vote_count",
        "ensemble_vote_ratio",
        "regime_transition_score",
        "turnover_pressure",
        "capacity_usage_ratio",
        "correlation_crowding_score",
    }
    assert result.get_column("freshness").to_list() == pytest.approx([0.8333333333, 0.0, 0.0])
    assert result.get_column("stale").to_list() == pytest.approx([1.0, 6.0, 8.0])
    assert result.get_column("quality").to_list() == pytest.approx([0.9, 0.6, 0.4])
    assert result.get_column("votes").to_list() == pytest.approx([2.0, 1.0, 1.0])
    assert result.get_column("vote_ratio").to_list() == pytest.approx([2 / 3, 1 / 3, 1 / 3])
    assert result.get_column("regime").to_list() == pytest.approx([0.4, -0.1, 0.0])
    assert result.get_column("turnover").to_list() == pytest.approx([0.05, None, 0.5])
    assert result.get_column("capacity").to_list() == pytest.approx([0.2, None, 0.5])
    assert result.get_column("crowding").to_list() == pytest.approx([0.48, 0.4, 0.0])


def test_drawdown_expression_computes_path_dependent_ops() -> None:
    frame = pl.DataFrame(
        {
            "canonical_symbol": ["QQQ", "QQQ", "QQQ", "QQQ", "QQQ"],
            "ts": [1, 2, 3, 4, 5],
            "price": [100.0, 120.0, 90.0, 110.0, 80.0],
        }
    )

    result = frame.with_columns(
        [
            drawdown_expression(
                DerivedFeature(
                    name="current_drawdown",
                    op="drawdown_from_peak",
                    columns=["price"],
                    window=3,
                )
            ).alias("current_drawdown"),
            drawdown_expression(
                DerivedFeature(
                    name="worst_drawdown",
                    op="rolling_max_drawdown",
                    columns=["price"],
                    window=3,
                )
            ).alias("worst_drawdown"),
            drawdown_expression(
                DerivedFeature(
                    name="duration",
                    op="drawdown_duration",
                    columns=["price"],
                    window=3,
                )
            ).alias("duration"),
        ]
    )

    assert DRAWDOWN_DERIVED_OPS == {
        "drawdown_from_peak",
        "rolling_max_drawdown",
        "drawdown_duration",
    }
    assert result.get_column("current_drawdown").to_list() == pytest.approx(
        [0.0, 0.0, -0.25, -0.0833333333, -0.2727272727]
    )
    assert result.get_column("worst_drawdown").to_list() == pytest.approx(
        [0.0, 0.0, -0.25, -0.25, -0.2727272727]
    )
    assert result.get_column("duration").to_list() == pytest.approx([0.0, 0.0, 1.0, 2.0, 1.0])


def test_external_signal_expression_computes_signal_and_score_ops() -> None:
    frame = pl.DataFrame(
        {
            "exchange_inflow": [300.0, 100.0],
            "exchange_outflow": [200.0, 250.0],
            "active_addresses": [900.0, 100.0],
            "active_address_baseline": [1000.0, 0.0],
            "sentiment_score": [0.3, -0.4],
            "sentiment_confidence": [0.8, 0.5],
            "reported_eps": [1.9, 2.4],
            "expected_eps": [2.0, 2.0],
            "fair_value": [101.0, 90.0],
            "research_close": [100.0, 0.0],
            "factor_score": [0.2, -0.3],
            "factor_volatility": [0.3, -0.6],
            "forecast_volatility": [0.5, 0.0],
        }
    )

    result = frame.with_columns(
        [
            external_signal_expression(
                DerivedFeature(
                    name="net_flow",
                    op="net_exchange_flow",
                    columns=["exchange_inflow", "exchange_outflow"],
                )
            ).alias("net_flow"),
            external_signal_expression(
                DerivedFeature(
                    name="activity",
                    op="onchain_activity_ratio",
                    columns=["active_addresses", "active_address_baseline"],
                )
            ).alias("activity"),
            external_signal_expression(
                DerivedFeature(
                    name="sentiment",
                    op="sentiment_weighted_score",
                    columns=["sentiment_score", "sentiment_confidence"],
                )
            ).alias("sentiment"),
            external_signal_expression(
                DerivedFeature(
                    name="surprise",
                    op="event_surprise",
                    columns=["reported_eps", "expected_eps"],
                )
            ).alias("surprise"),
            external_signal_expression(
                DerivedFeature(
                    name="value_gap",
                    op="fundamental_value_gap",
                    columns=["fair_value", "research_close"],
                )
            ).alias("value_gap"),
            external_signal_expression(
                DerivedFeature(
                    name="risk_score",
                    op="risk_adjusted_score",
                    columns=["factor_score", "factor_volatility"],
                )
            ).alias("risk_score"),
            external_signal_expression(
                DerivedFeature(
                    name="inv_vol",
                    op="inverse_volatility_weight",
                    columns=["forecast_volatility"],
                )
            ).alias("inv_vol"),
        ]
    )

    assert EXTERNAL_SIGNAL_DERIVED_OPS == {
        "net_exchange_flow",
        "onchain_activity_ratio",
        "sentiment_weighted_score",
        "event_surprise",
        "fundamental_value_gap",
        "risk_adjusted_score",
        "inverse_volatility_weight",
    }
    assert result.get_column("net_flow").to_list() == pytest.approx([100.0, -150.0])
    assert result.get_column("activity").to_list() == pytest.approx([0.9, None])
    assert result.get_column("sentiment").to_list() == pytest.approx([0.24, -0.2])
    assert result.get_column("surprise").to_list() == pytest.approx([-0.1, 0.4])
    assert result.get_column("value_gap").to_list() == pytest.approx([0.01, None])
    assert result.get_column("risk_score").to_list() == pytest.approx([2 / 3, -0.5])
    assert result.get_column("inv_vol").to_list() == pytest.approx([2.0, None])


def test_bands_channel_expression_computes_price_envelope_ops() -> None:
    frame = pl.DataFrame(
        {
            "canonical_symbol": ["QQQ", "QQQ", "QQQ", "QQQ"],
            "ts": [1, 2, 3, 4],
            "high": [10.0, 12.0, 13.0, 15.0],
            "low": [8.0, 9.0, 11.0, 12.0],
            "close": [9.0, 11.0, 12.0, 14.0],
        }
    )

    result = frame.with_columns(
        [
            bands_channel_expression(
                DerivedFeature(
                    name="tr",
                    op="true_range",
                    columns=["high", "low", "close"],
                    window=3,
                )
            ).alias("tr"),
            bands_channel_expression(
                DerivedFeature(name="atr", op="atr", columns=["high", "low", "close"], window=3)
            ).alias("atr"),
            bands_channel_expression(
                DerivedFeature(
                    name="bb_upper",
                    op="bollinger_upper",
                    columns=["close"],
                    window=3,
                    value=2.0,
                )
            ).alias("bb_upper"),
            bands_channel_expression(
                DerivedFeature(
                    name="bb_lower",
                    op="bollinger_lower",
                    columns=["close"],
                    window=3,
                    value=2.0,
                )
            ).alias("bb_lower"),
            bands_channel_expression(
                DerivedFeature(
                    name="bb_width",
                    op="bollinger_width",
                    columns=["close"],
                    window=3,
                    value=2.0,
                )
            ).alias("bb_width"),
            bands_channel_expression(
                DerivedFeature(
                    name="bb_percent_b",
                    op="bollinger_percent_b",
                    columns=["close"],
                    window=3,
                    value=2.0,
                )
            ).alias("bb_percent_b"),
            bands_channel_expression(
                DerivedFeature(
                    name="don_upper",
                    op="donchian_upper",
                    columns=["high", "low"],
                    window=3,
                )
            ).alias("don_upper"),
            bands_channel_expression(
                DerivedFeature(
                    name="don_lower",
                    op="donchian_lower",
                    columns=["high", "low"],
                    window=3,
                )
            ).alias("don_lower"),
            bands_channel_expression(
                DerivedFeature(
                    name="don_mid",
                    op="donchian_mid",
                    columns=["high", "low"],
                    window=3,
                )
            ).alias("don_mid"),
            bands_channel_expression(
                DerivedFeature(
                    name="don_width",
                    op="donchian_width",
                    columns=["high", "low"],
                    window=3,
                )
            ).alias("don_width"),
            bands_channel_expression(
                DerivedFeature(
                    name="kel_upper",
                    op="keltner_upper",
                    columns=["high", "low", "close"],
                    window=3,
                    value=2.0,
                )
            ).alias("kel_upper"),
            bands_channel_expression(
                DerivedFeature(
                    name="kel_lower",
                    op="keltner_lower",
                    columns=["high", "low", "close"],
                    window=3,
                    value=2.0,
                )
            ).alias("kel_lower"),
            bands_channel_expression(
                DerivedFeature(
                    name="kel_width",
                    op="keltner_width",
                    columns=["high", "low", "close"],
                    window=3,
                    value=2.0,
                )
            ).alias("kel_width"),
        ]
    )

    assert BANDS_CHANNEL_DERIVED_OPS == {
        "true_range",
        "atr",
        "bollinger_upper",
        "bollinger_lower",
        "bollinger_width",
        "bollinger_percent_b",
        "donchian_upper",
        "donchian_lower",
        "donchian_mid",
        "donchian_width",
        "keltner_upper",
        "keltner_lower",
        "keltner_width",
    }
    assert result.get_column("tr").to_list() == pytest.approx([2.0, 3.0, 2.0, 3.0])
    assert result.get_column("atr").to_list() == pytest.approx(
        [2.0, 2.5, 2.3333333333, 2.6666666667]
    )
    assert result.get_column("bb_upper").to_list() == pytest.approx(
        [None, 12.8284271247, 13.72171713, 15.3883837966]
    )
    assert result.get_column("bb_lower").to_list() == pytest.approx(
        [None, 7.1715728753, 7.6116162034, 9.27828287]
    )
    assert result.get_column("bb_width").to_list() == pytest.approx(
        [None, 0.5656854249, 0.5728219619, 0.4954135886]
    )
    assert result.get_column("bb_percent_b").to_list() == pytest.approx(
        [None, 0.6767766953, 0.7182178902, 0.7727723628]
    )
    assert result.get_column("don_upper").to_list() == pytest.approx([10.0, 12.0, 13.0, 15.0])
    assert result.get_column("don_lower").to_list() == pytest.approx([8.0, 8.0, 8.0, 9.0])
    assert result.get_column("don_mid").to_list() == pytest.approx([9.0, 10.0, 10.5, 12.0])
    assert result.get_column("don_width").to_list() == pytest.approx([2 / 9, 0.4, 10 / 21, 0.5])
    assert result.get_column("kel_upper").to_list() == pytest.approx(
        [13.0, 15.0, 15.6666666667, 17.8333333333]
    )
    assert result.get_column("kel_lower").to_list() == pytest.approx(
        [5.0, 5.0, 6.3333333333, 7.1666666667]
    )
    assert result.get_column("kel_width").to_list() == pytest.approx(
        [8 / 9, 1.0, 0.8484848485, 0.8533333333]
    )


def test_trend_indicator_expression_computes_trend_ops() -> None:
    frame = pl.DataFrame(
        {
            "canonical_symbol": ["QQQ", "QQQ", "QQQ", "QQQ", "QQQ"],
            "ts": [1, 2, 3, 4, 5],
            "high": [101.0, 102.0, 104.0, 106.0, 108.0],
            "low": [99.0, 100.0, 101.0, 103.0, 105.0],
            "close": [100.0, 101.0, 103.0, 105.0, 107.0],
        }
    )

    result = frame.with_columns(
        [
            trend_indicator_expression(
                DerivedFeature(
                    name="ich_conv",
                    op="ichimoku_conversion",
                    columns=["high", "low"],
                    window=3,
                )
            ).alias("ich_conv"),
            trend_indicator_expression(
                DerivedFeature(
                    name="ich_base",
                    op="ichimoku_base",
                    columns=["high", "low"],
                    window=4,
                )
            ).alias("ich_base"),
        ]
    ).with_columns(
        [
            trend_indicator_expression(
                DerivedFeature(
                    name="ich_a",
                    op="ichimoku_span_a",
                    columns=["ich_conv", "ich_base"],
                )
            ).alias("ich_a"),
            trend_indicator_expression(
                DerivedFeature(
                    name="ich_b",
                    op="ichimoku_span_b",
                    columns=["high", "low"],
                    window=5,
                )
            ).alias("ich_b"),
            trend_indicator_expression(
                DerivedFeature(
                    name="macd",
                    op="macd_line",
                    columns=["close"],
                    window=2,
                    value=4.0,
                )
            ).alias("macd"),
            trend_indicator_expression(
                DerivedFeature(
                    name="stoch_k",
                    op="stochastic_k",
                    columns=["high", "low", "close"],
                    window=3,
                )
            ).alias("stoch_k"),
            trend_indicator_expression(
                DerivedFeature(
                    name="adx",
                    op="adx",
                    columns=["high", "low", "close"],
                    window=3,
                )
            ).alias("adx"),
        ]
    )
    result = result.with_columns(
        trend_indicator_expression(
            DerivedFeature(
                name="stoch_d",
                op="stochastic_d",
                columns=["stoch_k"],
                window=2,
            )
        ).alias("stoch_d")
    )

    assert TREND_INDICATOR_DERIVED_OPS == {
        "ichimoku_conversion",
        "ichimoku_base",
        "ichimoku_span_b",
        "ichimoku_span_a",
        "macd_line",
        "stochastic_k",
        "stochastic_d",
        "adx",
    }
    assert result.get_column("ich_conv").to_list() == pytest.approx(
        [100.0, 100.5, 101.5, 103.0, 104.5]
    )
    assert result.get_column("ich_base").to_list() == pytest.approx(
        [100.0, 100.5, 101.5, 102.5, 104.0]
    )
    assert result.get_column("ich_a").to_list() == pytest.approx(
        [100.0, 100.5, 101.5, 102.75, 104.25]
    )
    assert result.get_column("ich_b").to_list() == pytest.approx(
        [100.0, 100.5, 101.5, 102.5, 103.5]
    )
    assert result.get_column("macd").to_list() == pytest.approx(
        [0.0, 0.2666666667, 0.7822222222, 1.2100740741, 1.506291358]
    )
    assert result.get_column("stoch_k").to_list() == pytest.approx(
        [50.0, 66.6666666667, 80.0, 83.3333333333, 85.7142857143]
    )
    assert result.get_column("stoch_d").to_list() == pytest.approx(
        [50.0, 58.3333333333, 73.3333333333, 81.6666666667, 84.5238095238]
    )
    assert result.get_column("adx").to_list() == pytest.approx([None, 100.0, 100.0, 100.0, 100.0])


def test_volume_indicator_expression_computes_volume_ops() -> None:
    frame = pl.DataFrame(
        {
            "canonical_symbol": ["QQQ", "QQQ", "QQQ", "QQQ", "QQQ"],
            "ts": [1, 2, 3, 4, 5],
            "close": [100.0, 102.0, 101.0, 103.0, 103.0],
            "volume": [1000.0, 1500.0, 1200.0, 1800.0, 900.0],
        }
    )

    result = frame.with_columns(
        [
            volume_indicator_expression(
                DerivedFeature(
                    name="obv",
                    op="obv",
                    columns=["close", "volume"],
                )
            ).alias("obv"),
            volume_indicator_expression(
                DerivedFeature(
                    name="vol_z",
                    op="volume_zscore",
                    columns=["volume"],
                    window=3,
                )
            ).alias("vol_z"),
        ]
    )

    assert VOLUME_INDICATOR_DERIVED_OPS == {
        "obv",
        "volume_zscore",
    }
    assert result.get_column("obv").to_list() == pytest.approx([0.0, 1500.0, 300.0, 2100.0, 2100.0])
    assert result.get_column("vol_z").to_list() == pytest.approx(
        [None, 0.7071067812, -0.1324532357, 1.0, -0.8728715609]
    )
