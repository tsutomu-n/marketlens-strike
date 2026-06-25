from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sis.research.strategy_lab.authoring.compiler.row_values import _sizing_value
from sis.research.strategy_lab.authoring.compiler.signal_sizing import (
    _signal_notional_usd,
    _signal_position_weight,
)
from sis.research.strategy_lab.authoring.contracts.spec import StrategyAuthoringSpec


@dataclass(frozen=True)
class _MultiLegBaseSizing:
    position_weight: float | None
    notional_usd: float | None


def _multi_leg_base_sizing(
    *, row: dict[str, Any], spec: StrategyAuthoringSpec
) -> _MultiLegBaseSizing:
    return _MultiLegBaseSizing(
        position_weight=_sizing_value(
            row,
            fixed=_signal_position_weight(row, spec),
            column=None,
        ),
        notional_usd=_sizing_value(
            row,
            fixed=_signal_notional_usd(row, spec),
            column=None,
        ),
    )
