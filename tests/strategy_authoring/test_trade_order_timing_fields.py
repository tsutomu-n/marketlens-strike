from __future__ import annotations

from types import SimpleNamespace

import pytest

from sis.research.strategy_lab.authoring.compiler.trade_order_timing_fields import (
    _trade_order_timing_fields,
)
from sis.research.strategy_lab.authoring.contracts.base import (
    StrategyAuthoringValidationError,
)


def _order(**overrides):
    defaults = {
        "timeout_minutes": None,
        "timeout_minutes_column": None,
        "time_in_force": "gtc",
        "time_in_force_column": None,
    }
    return SimpleNamespace(**{**defaults, **overrides})


def test_trade_order_timing_fields_resolve_defaults() -> None:
    assert _trade_order_timing_fields(row={}, order=_order()) == {
        "entry_timeout_minutes": None,
        "entry_time_in_force": "gtc",
    }


def test_trade_order_timing_fields_preserve_override_precedence() -> None:
    fields = _trade_order_timing_fields(
        row={"row_timeout": 45, "row_tif": "ioc"},
        order=_order(
            timeout_minutes_column="row_timeout",
            time_in_force_column="row_tif",
        ),
        order_overrides={
            "timeout_minutes": 30,
            "time_in_force": "gtd",
        },
    )

    assert fields == {
        "entry_timeout_minutes": 30,
        "entry_time_in_force": "gtd",
    }


def test_trade_order_timing_fields_require_timeout_for_gtd() -> None:
    with pytest.raises(
        StrategyAuthoringValidationError,
        match="timeout_minutes or timeout_minutes_column is required",
    ):
        _trade_order_timing_fields(row={}, order=_order(time_in_force="gtd"))


def test_trade_order_timing_fields_reject_timeout_for_ioc_or_fok() -> None:
    for time_in_force in ("ioc", "fok"):
        with pytest.raises(
            StrategyAuthoringValidationError,
            match="timeout_minutes cannot be set",
        ):
            _trade_order_timing_fields(
                row={},
                order=_order(time_in_force=time_in_force, timeout_minutes=5),
            )
