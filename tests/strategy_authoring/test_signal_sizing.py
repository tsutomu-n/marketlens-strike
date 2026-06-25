from __future__ import annotations

from types import SimpleNamespace

import pytest

from sis.research.strategy_lab.authoring.compiler.signal_sizing import (
    _signal_notional_usd,
    _signal_position_weight,
)
from sis.research.strategy_lab.authoring.contracts.core import Condition, EntryRules
from sis.research.strategy_lab.authoring.contracts.multi_leg import RegimeOverride


def _spec(*, sizing: object, regime_overrides: list[RegimeOverride] | None = None):
    return SimpleNamespace(
        rules=SimpleNamespace(
            sizing=sizing,
            regime_overrides=regime_overrides or [],
        )
    )


def _sizing(**overrides):
    defaults = {
        "position_weight": None,
        "position_weight_column": None,
        "notional_usd": None,
        "notional_usd_column": None,
        "volatility_target": None,
        "volatility_column": None,
        "max_volatility_scaled_position_weight": None,
    }
    return SimpleNamespace(**{**defaults, **overrides})


def test_signal_position_weight_resolves_fixed_column_and_volatility_scaling() -> None:
    spec = _spec(
        sizing=_sizing(
            position_weight=1.0,
            position_weight_column="row_weight",
            volatility_target=0.2,
            volatility_column="realized_vol",
            max_volatility_scaled_position_weight=1.5,
        )
    )

    assert _signal_position_weight({"row_weight": 0.8, "realized_vol": 0.1}, spec) == 1.5
    assert _signal_position_weight({"row_weight": 0.8, "realized_vol": 0.4}, spec) == pytest.approx(
        0.4
    )


def test_signal_position_weight_falls_back_when_volatility_is_missing_or_invalid() -> None:
    spec = _spec(
        sizing=_sizing(
            position_weight=1.0,
            volatility_target=0.2,
            volatility_column="realized_vol",
        )
    )

    assert _signal_position_weight({}, spec) == 1.0
    assert _signal_position_weight({"realized_vol": 0.0}, spec) == 1.0
    assert _signal_position_weight({"realized_vol": -0.1}, spec) == 1.0


def test_signal_notional_usd_resolves_row_column() -> None:
    spec = _spec(sizing=_sizing(notional_usd=1000.0, notional_usd_column="row_notional"))

    assert _signal_notional_usd({"row_notional": "1250.5"}, spec) == 1250.5
    assert _signal_notional_usd({}, spec) == 1000.0


def test_signal_sizing_uses_matching_regime_fallbacks() -> None:
    regime = RegimeOverride(
        name="high_vol",
        when=EntryRules(all=[Condition(column="vix_level", op="gte", value=25)]),
        position_weight=0.25,
        notional_usd=500.0,
    )
    spec = _spec(
        sizing=_sizing(position_weight=1.0, notional_usd=1000.0),
        regime_overrides=[regime],
    )

    assert _signal_position_weight({"vix_level": 20.0}, spec) == 1.0
    assert _signal_notional_usd({"vix_level": 20.0}, spec) == 1000.0
    assert _signal_position_weight({"vix_level": 26.0}, spec) == 0.25
    assert _signal_notional_usd({"vix_level": 26.0}, spec) == 500.0
