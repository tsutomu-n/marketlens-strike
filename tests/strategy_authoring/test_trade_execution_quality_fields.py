from __future__ import annotations

from types import SimpleNamespace

from sis.research.strategy_lab.authoring.compiler.trade_execution_quality_fields import (
    _trade_execution_quality_fields,
)


def _execution(**overrides):
    defaults = {
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
    }
    return SimpleNamespace(**{**defaults, **overrides})


def _regime(**overrides):
    defaults = {
        "max_fill_fraction": None,
        "min_fill_fraction": None,
        "max_spread_bps": None,
        "min_depth_usd": None,
        "depth_participation_rate": None,
        "max_latency_ms": None,
        "min_queue_position_score": None,
    }
    return SimpleNamespace(**{**defaults, **overrides})


def test_trade_execution_quality_fields_resolve_defaults() -> None:
    assert _trade_execution_quality_fields(row={}, execution=_execution()) == {
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
    }


def test_trade_execution_quality_fields_use_row_columns_overrides_and_regime() -> None:
    fields = _trade_execution_quality_fields(
        row={
            "row_max_fill": 0.8,
            "row_min_fill": 0.25,
            "row_max_spread": 5.0,
            "row_min_depth": 99_999.0,
            "row_max_latency": 30.0,
            "latency_override": "12",
            "row_min_queue": 0.35,
            "queue_score": 0.7,
        },
        execution=_execution(
            max_fill_fraction_column="row_max_fill",
            min_fill_fraction_column="row_min_fill",
            max_spread_bps_column="row_max_spread",
            min_depth_usd_column="row_min_depth",
            max_latency_ms_column="row_max_latency",
            min_queue_position_score_column="row_min_queue",
            queue_position_score_column="queue_score",
        ),
        regime=_regime(
            max_fill_fraction=0.5,
            min_depth_usd=3_000.0,
            depth_participation_rate=0.15,
        ),
        execution_overrides={
            "min_depth_usd": 2_000.0,
            "depth_column": "depth_override",
            "depth_participation_rate": 0.2,
            "latency_column": "latency_override",
        },
    )

    assert fields == {
        "max_fill_fraction": 0.8,
        "min_fill_fraction": 0.25,
        "max_spread_bps": 5.0,
        "min_depth_usd": 2_000.0,
        "depth_column": "depth_override",
        "depth_participation_rate": 0.2,
        "max_latency_ms": 30.0,
        "latency_ms": 12.0,
        "min_queue_position_score": 0.35,
        "queue_position_score": 0.7,
    }
