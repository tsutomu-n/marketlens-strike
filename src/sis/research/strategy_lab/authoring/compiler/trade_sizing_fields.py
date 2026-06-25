from __future__ import annotations

from typing import Any

from sis.research.strategy_lab.authoring.compiler.signal_sizing import (
    _signal_notional_usd,
    _signal_position_weight,
)
from sis.research.strategy_lab.authoring.contracts.spec import StrategyAuthoringSpec


def _trade_sizing_fields(
    *,
    spec: StrategyAuthoringSpec,
    row: dict[str, Any],
    position_weight: float | None,
    notional_usd: float | None,
) -> dict[str, float | None]:
    return {
        "position_weight": position_weight
        if position_weight is not None
        else _signal_position_weight(row, spec),
        "notional_usd": notional_usd
        if notional_usd is not None
        else _signal_notional_usd(row, spec),
    }
