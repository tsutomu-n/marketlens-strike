from __future__ import annotations

from typing import Any

from sis.research.strategy_lab.authoring.compiler.common import (
    _matching_regime_override,
    _regime_value,
)
from sis.research.strategy_lab.authoring.compiler.row_values import (
    _optional_float_from_row,
    _sizing_value,
)
from sis.research.strategy_lab.authoring.contracts.spec import StrategyAuthoringSpec


def _signal_position_weight(row: dict[str, Any], spec: StrategyAuthoringSpec) -> float | None:
    regime = _matching_regime_override(row, spec)
    fixed = _regime_value(regime, "position_weight", spec.rules.sizing.position_weight)
    base = _sizing_value(row, fixed=fixed, column=spec.rules.sizing.position_weight_column)
    if (
        base is None
        or spec.rules.sizing.volatility_target is None
        or spec.rules.sizing.volatility_column is None
    ):
        return base
    observed = _optional_float_from_row(row, spec.rules.sizing.volatility_column)
    if observed is None or observed <= 0:
        return base
    scaled = base * spec.rules.sizing.volatility_target / observed
    cap = spec.rules.sizing.max_volatility_scaled_position_weight
    return min(scaled, cap) if cap is not None else scaled


def _signal_notional_usd(row: dict[str, Any], spec: StrategyAuthoringSpec) -> float | None:
    regime = _matching_regime_override(row, spec)
    fixed = _regime_value(regime, "notional_usd", spec.rules.sizing.notional_usd)
    return _sizing_value(row, fixed=fixed, column=spec.rules.sizing.notional_usd_column)
