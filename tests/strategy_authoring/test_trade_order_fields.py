from __future__ import annotations

from types import SimpleNamespace

import pytest

from sis.research.strategy_lab.authoring.compiler.trade_order_fields import (
    _trade_order_fields,
)
from sis.research.strategy_lab.authoring.contracts.base import (
    StrategyAuthoringValidationError,
)


def _order(**overrides):
    defaults = {
        "reduce_only": False,
        "reduce_only_column": None,
        "timeout_minutes": None,
        "timeout_minutes_column": None,
        "time_in_force": "gtc",
        "time_in_force_column": None,
        "entry_type": "market",
        "entry_type_column": None,
        "limit_offset_bps": None,
        "limit_offset_bps_column": None,
        "stop_offset_bps": None,
        "stop_offset_bps_column": None,
        "post_only": False,
        "post_only_column": None,
    }
    return SimpleNamespace(**{**defaults, **overrides})


def test_trade_order_fields_resolve_defaults() -> None:
    fields = _trade_order_fields(row={}, order=_order())

    assert fields == {
        "entry_order_type": "market",
        "entry_limit_offset_bps": None,
        "entry_stop_offset_bps": None,
        "entry_timeout_minutes": None,
        "entry_time_in_force": "gtc",
        "entry_post_only": False,
        "entry_reduce_only": False,
    }


def test_trade_order_fields_use_row_columns_and_leg_overrides() -> None:
    fields = _trade_order_fields(
        row={
            "row_entry_type": "limit",
            "row_limit_offset": 25.0,
            "row_tif": "gtd",
            "row_timeout": 45,
            "row_post_only": "yes",
            "row_reduce_only": "true",
        },
        order=_order(
            entry_type="market",
            entry_type_column="row_entry_type",
            limit_offset_bps_column="row_limit_offset",
            time_in_force_column="row_tif",
            timeout_minutes_column="row_timeout",
            post_only_column="row_post_only",
            reduce_only_column="row_reduce_only",
        ),
        order_overrides={
            "entry_type": "limit",
            "limit_offset_bps": 10.0,
            "time_in_force": "gtd",
            "timeout_minutes": 30,
            "post_only": True,
            "reduce_only": True,
        },
    )

    assert fields == {
        "entry_order_type": "limit",
        "entry_limit_offset_bps": 10.0,
        "entry_stop_offset_bps": None,
        "entry_timeout_minutes": 30,
        "entry_time_in_force": "gtd",
        "entry_post_only": True,
        "entry_reduce_only": True,
    }


def test_trade_order_fields_require_timeout_for_gtd() -> None:
    with pytest.raises(
        StrategyAuthoringValidationError,
        match="timeout_minutes or timeout_minutes_column is required",
    ):
        _trade_order_fields(row={}, order=_order(time_in_force="gtd"))


def test_trade_order_fields_reject_timeout_for_ioc() -> None:
    with pytest.raises(
        StrategyAuthoringValidationError,
        match="timeout_minutes cannot be set",
    ):
        _trade_order_fields(row={}, order=_order(time_in_force="ioc", timeout_minutes=5))


def test_trade_order_fields_require_offsets_for_selected_entry_type() -> None:
    with pytest.raises(StrategyAuthoringValidationError, match="row entry_type is limit"):
        _trade_order_fields(row={}, order=_order(entry_type="limit"))

    with pytest.raises(StrategyAuthoringValidationError, match="row entry_type is stop_market"):
        _trade_order_fields(row={}, order=_order(entry_type="stop_market"))


def test_trade_order_fields_reject_post_only_for_non_limit() -> None:
    with pytest.raises(StrategyAuthoringValidationError, match="post_only is only supported"):
        _trade_order_fields(row={}, order=_order(entry_type="market", post_only=True))
