from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from sis.research.strategy_lab.authoring.compiler.position_entry_limits import (
    _position_entry_limit_block_reason,
)
from sis.research.strategy_lab.authoring.compiler.position_marker_transition import (
    _apply_position_marker_transition,
)
from sis.research.strategy_lab.authoring.compiler.position_reduce_only_transition import (
    _apply_reduce_only_entry_transition,
)
from sis.research.strategy_lab.authoring.compiler.position_state import ActivePosition
from sis.research.strategy_lab.authoring.compiler.portfolio_weight_values import (
    _position_weight_value,
)
from sis.research.strategy_lab.authoring.compiler.trade_blocking import _block_trade_row
from sis.research.strategy_lab.authoring.contracts.spec import StrategyAuthoringSpec


@dataclass(frozen=True)
class _PositionRowState:
    selected_row: dict[str, Any]
    active: list[ActivePosition]


def _apply_position_row_state(
    *,
    row: dict[str, Any],
    spec: StrategyAuthoringSpec,
    active: list[ActivePosition],
    open_weight: float,
    ts_signal: datetime,
    horizon_minutes: int,
) -> _PositionRowState:
    side = str(row.get("side") or "")
    if side in {"close", "reduce", "add", "rebalance"}:
        selected_row, updated_active = _apply_position_marker_transition(
            row=row,
            spec=spec,
            active=active,
            open_weight=open_weight,
        )
        return _PositionRowState(selected_row=selected_row, active=updated_active)

    if row.get("entry_reduce_only") and side in {"long", "short"}:
        selected_row, updated_active = _apply_reduce_only_entry_transition(
            row=row,
            spec=spec,
            active=active,
            side=side,
        )
        return _PositionRowState(selected_row=selected_row, active=updated_active)

    weight = abs(_position_weight_value(row))
    block_reason = _position_entry_limit_block_reason(
        position=spec.rules.position,
        active=active,
        open_weight=open_weight,
        side=side,
        weight=weight,
    )
    if block_reason is not None:
        return _PositionRowState(
            selected_row=_block_trade_row(row, spec=spec, block_reason=block_reason),
            active=active,
        )

    updated_active = [*active, (ts_signal + timedelta(minutes=horizon_minutes), side, weight)]
    return _PositionRowState(selected_row=row, active=updated_active)
