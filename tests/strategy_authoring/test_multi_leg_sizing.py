import pytest

from sis.research.strategy_lab.authoring.compiler.multi_leg_sizing import (
    _multi_leg_sizing_fields,
)
from sis.research.strategy_lab.authoring.contracts.multi_leg import MultiLegEntry


def test_multi_leg_sizing_fields_multiply_base_and_leg_weights() -> None:
    leg = MultiLegEntry(
        real_market_symbol="BBB",
        side="opposite",
        position_weight=0.4,
    )

    assert _multi_leg_sizing_fields(
        row={},
        leg=leg,
        base_weight=2.0,
        base_notional=1000.0,
    ) == {
        "position_weight": 0.8,
        "notional_usd": 400.0,
    }


def test_multi_leg_sizing_fields_use_column_weight_for_weight_and_base_notional() -> None:
    leg = MultiLegEntry(
        real_market_symbol="BBB",
        side="opposite",
        position_weight=0.4,
        position_weight_column="hedge_ratio",
    )

    result = _multi_leg_sizing_fields(
        row={"hedge_ratio": "0.75"},
        leg=leg,
        base_weight=2.0,
        base_notional=1000.0,
    )

    assert result["position_weight"] == pytest.approx(1.5)
    assert result["notional_usd"] == pytest.approx(750.0)


def test_multi_leg_sizing_fields_prefer_explicit_leg_notional() -> None:
    leg = MultiLegEntry(
        real_market_symbol="BBB",
        side="opposite",
        position_weight=0.4,
        notional_usd=725.0,
    )

    assert _multi_leg_sizing_fields(
        row={},
        leg=leg,
        base_weight=2.0,
        base_notional=1000.0,
    ) == {
        "position_weight": 0.8,
        "notional_usd": 725.0,
    }


def test_multi_leg_sizing_fields_prefer_dynamic_leg_notional() -> None:
    leg = MultiLegEntry(
        real_market_symbol="BBB",
        side="opposite",
        position_weight=0.4,
        notional_usd=725.0,
        notional_usd_column="hedge_notional",
    )

    assert _multi_leg_sizing_fields(
        row={"hedge_notional": "810.5"},
        leg=leg,
        base_weight=2.0,
        base_notional=1000.0,
    ) == {
        "position_weight": 0.8,
        "notional_usd": 810.5,
    }


def test_multi_leg_sizing_fields_handle_absent_base_values() -> None:
    leg = MultiLegEntry(
        real_market_symbol="BBB",
        side="opposite",
    )

    assert _multi_leg_sizing_fields(
        row={},
        leg=leg,
        base_weight=None,
        base_notional=None,
    ) == {
        "position_weight": 1.0,
        "notional_usd": None,
    }
