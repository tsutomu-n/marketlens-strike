from __future__ import annotations

from types import SimpleNamespace

import pytest

from sis.research.strategy_lab.authoring.compiler.trade_order_price_fields import (
    _trade_order_price_fields,
)
from sis.research.strategy_lab.authoring.contracts.base import (
    StrategyAuthoringValidationError,
)


def _order(**overrides):
    defaults = {
        "entry_type": "market",
        "entry_type_column": None,
        "limit_offset_bps": None,
        "limit_offset_bps_column": None,
        "stop_offset_bps": None,
        "stop_offset_bps_column": None,
    }
    return SimpleNamespace(**{**defaults, **overrides})


def test_trade_order_price_fields_resolve_defaults() -> None:
    assert _trade_order_price_fields(row={}, order=_order()) == {
        "entry_order_type": "market",
        "entry_limit_offset_bps": None,
        "entry_stop_offset_bps": None,
    }


def test_trade_order_price_fields_use_row_columns_and_overrides() -> None:
    fields = _trade_order_price_fields(
        row={
            "row_entry_type": "stop_market",
            "row_limit_offset": 25.0,
            "row_stop_offset": "12.5",
        },
        order=_order(
            entry_type_column="row_entry_type",
            limit_offset_bps_column="row_limit_offset",
            stop_offset_bps_column="row_stop_offset",
        ),
        order_overrides={
            "entry_type": "limit",
            "limit_offset_bps": 10.0,
        },
    )

    assert fields == {
        "entry_order_type": "limit",
        "entry_limit_offset_bps": 10.0,
        "entry_stop_offset_bps": 12.5,
    }


def test_trade_order_price_fields_require_offsets_for_selected_entry_type() -> None:
    with pytest.raises(StrategyAuthoringValidationError, match="row entry_type is limit"):
        _trade_order_price_fields(row={}, order=_order(entry_type="limit"))

    with pytest.raises(StrategyAuthoringValidationError, match="row entry_type is stop_market"):
        _trade_order_price_fields(row={}, order=_order(entry_type="stop_market"))
