from __future__ import annotations

from sis.research.strategy_lab.authoring.contracts.trade_controls import SizingRules
from sis.research.strategy_lab.authoring.sizing_required_columns import (
    _sizing_required_columns,
)


def test_sizing_required_columns_collects_explicit_sizing_columns() -> None:
    rules = SizingRules(
        position_weight_column="position_weight",
        notional_usd_column="notional",
        volatility_target=0.2,
        volatility_column="realized_vol",
    )

    assert _sizing_required_columns(rules) == {
        "position_weight",
        "notional",
        "realized_vol",
    }


def test_sizing_required_columns_returns_empty_set_when_disabled() -> None:
    assert _sizing_required_columns(SizingRules()) == set()
