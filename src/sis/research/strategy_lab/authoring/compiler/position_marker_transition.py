from __future__ import annotations

from typing import Any

from sis.research.strategy_lab.authoring.compiler.common import _block_trade_row
from sis.research.strategy_lab.authoring.compiler.position_state import (
    ActivePosition,
    _clamped_position_fraction,
    _compact_active_positions,
    _non_negative_position_value,
)
from sis.research.strategy_lab.authoring.contracts.spec import StrategyAuthoringSpec


def _apply_position_marker_transition(
    *,
    row: dict[str, Any],
    spec: StrategyAuthoringSpec,
    active: list[ActivePosition],
    open_weight: float,
) -> tuple[dict[str, Any], list[ActivePosition]]:
    position = spec.rules.position
    side = str(row.get("side") or "")
    if position.require_open_position_for_markers and open_weight <= 0:
        return (
            _block_trade_row(row, spec=spec, block_reason="position_marker_without_open"),
            active,
        )
    if side == "close":
        return row, []
    if side == "reduce" and open_weight > 0:
        fraction = _clamped_position_fraction(row.get("reduce_fraction"))
        return row, _compact_active_positions(active, open_weight * (1.0 - fraction))
    if side == "add" and open_weight > 0:
        added_weight = _non_negative_position_value(row.get("add_fraction"), default=1.0)
        if (
            position.max_open_position_weight_per_symbol is not None
            and open_weight + added_weight > position.max_open_position_weight_per_symbol
        ):
            return (
                _block_trade_row(row, spec=spec, block_reason="position_open_weight_limit"),
                active,
            )
        return row, _compact_active_positions(active, open_weight + added_weight)
    if side == "rebalance" and open_weight > 0:
        target_weight = _non_negative_position_value(
            row.get("rebalance_target_fraction"), default=open_weight
        )
        if (
            position.max_open_position_weight_per_symbol is not None
            and target_weight > position.max_open_position_weight_per_symbol
        ):
            return (
                _block_trade_row(row, spec=spec, block_reason="position_open_weight_limit"),
                active,
            )
        return row, _compact_active_positions(active, target_weight)
    return row, active
