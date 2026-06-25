from __future__ import annotations

from types import SimpleNamespace

from sis.research.strategy_lab.authoring.compiler.trade_execution_liquidity_fields import (
    _trade_execution_liquidity_fields,
)


def _execution(**overrides):
    defaults = {
        "max_spread_bps": None,
        "max_spread_bps_column": None,
        "min_depth_usd": None,
        "min_depth_usd_column": None,
        "depth_column": "min_side_depth_10bps_usd",
        "depth_participation_rate": 1.0,
    }
    return SimpleNamespace(**{**defaults, **overrides})


def _regime(**overrides):
    defaults = {
        "max_spread_bps": None,
        "min_depth_usd": None,
        "depth_participation_rate": None,
    }
    return SimpleNamespace(**{**defaults, **overrides})


def test_trade_execution_liquidity_fields_resolve_defaults() -> None:
    assert _trade_execution_liquidity_fields(row={}, execution=_execution()) == {
        "max_spread_bps": None,
        "min_depth_usd": None,
        "depth_column": "min_side_depth_10bps_usd",
        "depth_participation_rate": 1.0,
    }


def test_trade_execution_liquidity_fields_use_columns_overrides_and_regime() -> None:
    fields = _trade_execution_liquidity_fields(
        row={
            "row_max_spread": "5",
            "row_min_depth": 99_999.0,
        },
        execution=_execution(
            max_spread_bps_column="row_max_spread",
            min_depth_usd_column="row_min_depth",
        ),
        regime=_regime(
            max_spread_bps=8.0,
            min_depth_usd=3_000.0,
            depth_participation_rate=0.15,
        ),
        execution_overrides={
            "min_depth_usd": 2_000.0,
            "depth_column": "depth_override",
            "depth_participation_rate": 0.2,
        },
    )

    assert fields == {
        "max_spread_bps": 5.0,
        "min_depth_usd": 2_000.0,
        "depth_column": "depth_override",
        "depth_participation_rate": 0.2,
    }
