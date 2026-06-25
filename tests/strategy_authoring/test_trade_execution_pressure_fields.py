from __future__ import annotations

from types import SimpleNamespace

from sis.research.strategy_lab.authoring.compiler.trade_execution_pressure_fields import (
    _trade_execution_pressure_fields,
)


def _execution(**overrides):
    defaults = {
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
        "max_turnover_pressure": None,
        "max_capacity_usage_ratio": None,
        "max_correlation_crowding_score": None,
        "min_fee_edge_bps": None,
    }
    return SimpleNamespace(**{**defaults, **overrides})


def test_trade_execution_pressure_fields_resolve_defaults() -> None:
    assert _trade_execution_pressure_fields(row={}, execution=_execution()) == {
        "max_turnover_pressure": None,
        "turnover_pressure": None,
        "max_capacity_usage_ratio": None,
        "capacity_usage_ratio": None,
        "max_correlation_crowding_score": None,
        "correlation_crowding_score": None,
        "min_fee_edge_bps": None,
        "fee_edge_bps": None,
    }


def test_trade_execution_pressure_fields_use_row_columns_regime_and_column_overrides() -> None:
    fields = _trade_execution_pressure_fields(
        row={
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
            max_turnover_pressure_column="row_max_turnover",
            turnover_pressure_column="turnover",
            max_capacity_usage_ratio_column="row_max_capacity",
            capacity_usage_column="capacity",
            max_correlation_crowding_score_column="row_max_crowding",
            correlation_crowding_column="crowding",
            min_fee_edge_bps_column="row_min_fee_edge",
        ),
        regime=_regime(
            max_turnover_pressure=0.8,
            max_capacity_usage_ratio=0.7,
            max_correlation_crowding_score=0.6,
            min_fee_edge_bps=0.5,
        ),
        execution_overrides={"fee_edge_column": "fee_edge_override"},
    )

    assert fields == {
        "max_turnover_pressure": 0.4,
        "turnover_pressure": 0.3,
        "max_capacity_usage_ratio": 0.6,
        "capacity_usage_ratio": 0.55,
        "max_correlation_crowding_score": 0.45,
        "correlation_crowding_score": 0.2,
        "min_fee_edge_bps": 2.1,
        "fee_edge_bps": -1.25,
    }
