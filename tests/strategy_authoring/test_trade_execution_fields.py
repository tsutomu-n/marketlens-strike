from __future__ import annotations

from types import SimpleNamespace

from sis.research.strategy_lab.authoring.compiler.trade_execution_fields import (
    _trade_execution_fields,
)


def _execution(**overrides):
    defaults = {
        "slippage_bps": 0.0,
        "slippage_bps_column": None,
        "max_fill_fraction": 1.0,
        "max_fill_fraction_column": None,
        "min_fill_fraction": None,
        "min_fill_fraction_column": None,
        "max_spread_bps": None,
        "max_spread_bps_column": None,
        "min_depth_usd": None,
        "min_depth_usd_column": None,
        "depth_column": "min_side_depth_10bps_usd",
        "depth_participation_rate": 1.0,
        "max_latency_ms": None,
        "max_latency_ms_column": None,
        "latency_column": "latency_ms",
        "min_queue_position_score": None,
        "min_queue_position_score_column": None,
        "queue_position_score_column": "queue_position_score",
        "min_borrow_availability_ratio": None,
        "min_borrow_availability_ratio_column": None,
        "borrow_availability_column": "borrow_availability_ratio",
        "max_borrow_cost_bps": None,
        "max_borrow_cost_bps_column": None,
        "borrow_cost_column": "borrow_cost_bps",
        "max_tax_drag_bps": None,
        "max_tax_drag_bps_column": None,
        "tax_drag_column": "tax_drag_bps",
        "max_turnover_pressure": None,
        "max_turnover_pressure_column": None,
        "turnover_pressure_column": "turnover_pressure",
        "max_capacity_usage_ratio": None,
        "max_capacity_usage_ratio_column": None,
        "capacity_usage_column": "capacity_usage_ratio",
        "max_correlation_crowding_score": None,
        "max_correlation_crowding_score_column": None,
        "correlation_crowding_column": "correlation_crowding_score",
        "min_fee_edge_bps": None,
        "min_fee_edge_bps_column": None,
        "fee_edge_column": "maker_taker_fee_edge_bps",
    }
    return SimpleNamespace(**{**defaults, **overrides})


def _regime(**overrides):
    defaults = {
        "slippage_bps": None,
        "max_fill_fraction": None,
        "min_fill_fraction": None,
        "max_spread_bps": None,
        "min_depth_usd": None,
        "depth_participation_rate": None,
        "max_latency_ms": None,
        "min_queue_position_score": None,
        "min_borrow_availability_ratio": None,
        "max_borrow_cost_bps": None,
        "max_tax_drag_bps": None,
        "max_turnover_pressure": None,
        "max_capacity_usage_ratio": None,
        "max_correlation_crowding_score": None,
        "min_fee_edge_bps": None,
    }
    return SimpleNamespace(**{**defaults, **overrides})


def test_trade_execution_fields_resolve_defaults() -> None:
    fields = _trade_execution_fields(row={}, execution=_execution())

    assert fields == {
        "slippage_bps": 0.0,
        "max_fill_fraction": 1.0,
        "min_fill_fraction": None,
        "max_spread_bps": None,
        "min_depth_usd": None,
        "depth_column": "min_side_depth_10bps_usd",
        "depth_participation_rate": 1.0,
        "max_latency_ms": None,
        "latency_ms": None,
        "min_queue_position_score": None,
        "queue_position_score": None,
        "min_borrow_availability_ratio": None,
        "borrow_availability_ratio": None,
        "max_borrow_cost_bps": None,
        "borrow_cost_bps": None,
        "max_tax_drag_bps": None,
        "tax_drag_bps": None,
        "max_turnover_pressure": None,
        "turnover_pressure": None,
        "max_capacity_usage_ratio": None,
        "capacity_usage_ratio": None,
        "max_correlation_crowding_score": None,
        "correlation_crowding_score": None,
        "min_fee_edge_bps": None,
        "fee_edge_bps": None,
    }


def test_trade_execution_fields_use_row_columns_and_leg_overrides() -> None:
    fields = _trade_execution_fields(
        row={
            "row_slippage": 1.5,
            "row_max_fill": 0.8,
            "row_min_fill": 0.25,
            "row_max_spread": 5.0,
            "row_min_depth": 99_999.0,
            "row_max_latency": 30.0,
            "latency_override": "12",
            "row_min_queue": 0.35,
            "queue_score": 0.7,
            "row_min_borrow_availability": 0.9,
            "borrow_availability": 0.95,
            "row_max_borrow_cost": 3.5,
            "borrow_cost_override": "2.5",
            "row_max_tax_drag": 1.2,
            "tax_drag": 0.8,
            "row_max_turnover": 0.4,
            "turnover": 0.3,
            "row_max_capacity": 0.6,
            "capacity": 0.55,
            "row_max_crowding": 0.45,
            "crowding": 0.2,
            "row_min_fee_edge": 2.1,
            "fee_edge_override": "-1.25",
        },
        execution=_execution(
            slippage_bps_column="row_slippage",
            max_fill_fraction_column="row_max_fill",
            min_fill_fraction_column="row_min_fill",
            max_spread_bps_column="row_max_spread",
            min_depth_usd_column="row_min_depth",
            max_latency_ms_column="row_max_latency",
            min_queue_position_score_column="row_min_queue",
            queue_position_score_column="queue_score",
            min_borrow_availability_ratio_column="row_min_borrow_availability",
            borrow_availability_column="borrow_availability",
            max_borrow_cost_bps_column="row_max_borrow_cost",
            max_tax_drag_bps_column="row_max_tax_drag",
            tax_drag_column="tax_drag",
            max_turnover_pressure_column="row_max_turnover",
            turnover_pressure_column="turnover",
            max_capacity_usage_ratio_column="row_max_capacity",
            capacity_usage_column="capacity",
            max_correlation_crowding_score_column="row_max_crowding",
            correlation_crowding_column="crowding",
            min_fee_edge_bps_column="row_min_fee_edge",
        ),
        execution_overrides={
            "min_depth_usd": 2_000.0,
            "depth_column": "depth_override",
            "depth_participation_rate": 0.2,
            "latency_column": "latency_override",
            "borrow_cost_column": "borrow_cost_override",
            "fee_edge_column": "fee_edge_override",
        },
    )

    assert fields["slippage_bps"] == 1.5
    assert fields["max_fill_fraction"] == 0.8
    assert fields["min_fill_fraction"] == 0.25
    assert fields["max_spread_bps"] == 5.0
    assert fields["min_depth_usd"] == 2_000.0
    assert fields["depth_column"] == "depth_override"
    assert fields["depth_participation_rate"] == 0.2
    assert fields["max_latency_ms"] == 30.0
    assert fields["latency_ms"] == 12.0
    assert fields["min_queue_position_score"] == 0.35
    assert fields["queue_position_score"] == 0.7
    assert fields["min_borrow_availability_ratio"] == 0.9
    assert fields["borrow_availability_ratio"] == 0.95
    assert fields["max_borrow_cost_bps"] == 3.5
    assert fields["borrow_cost_bps"] == 2.5
    assert fields["max_tax_drag_bps"] == 1.2
    assert fields["tax_drag_bps"] == 0.8
    assert fields["max_turnover_pressure"] == 0.4
    assert fields["turnover_pressure"] == 0.3
    assert fields["max_capacity_usage_ratio"] == 0.6
    assert fields["capacity_usage_ratio"] == 0.55
    assert fields["max_correlation_crowding_score"] == 0.45
    assert fields["correlation_crowding_score"] == 0.2
    assert fields["min_fee_edge_bps"] == 2.1
    assert fields["fee_edge_bps"] == -1.25


def test_trade_execution_fields_use_regime_fallbacks() -> None:
    fields = _trade_execution_fields(
        row={},
        execution=_execution(),
        regime=_regime(
            slippage_bps=4.0,
            max_fill_fraction=0.5,
            min_depth_usd=3_000.0,
            depth_participation_rate=0.15,
            max_borrow_cost_bps=6.0,
            min_fee_edge_bps=0.7,
        ),
    )

    assert fields["slippage_bps"] == 4.0
    assert fields["max_fill_fraction"] == 0.5
    assert fields["min_depth_usd"] == 3_000.0
    assert fields["depth_participation_rate"] == 0.15
    assert fields["max_borrow_cost_bps"] == 6.0
    assert fields["min_fee_edge_bps"] == 0.7
