from __future__ import annotations

from sis.research.strategy_lab.authoring.compiler.position_state import ActivePosition
from sis.research.strategy_lab.authoring.contracts.risk_controls import PositionRules


def _position_entry_limit_block_reason(
    *,
    position: PositionRules,
    active: list[ActivePosition],
    open_weight: float,
    side: str,
    weight: float,
) -> str | None:
    if not position.allow_opposing_open_positions and side in {"long", "short"}:
        opposing_side = "short" if side == "long" else "long"
        opposing_weight = sum(
            active_weight
            for _end_at, active_side, active_weight in active
            if active_side == opposing_side
        )
        if opposing_weight > 0:
            return "position_opposing_open_position"
    if not position.allow_pyramiding and side in {"long", "short"}:
        same_side_weight = sum(
            active_weight for _end_at, active_side, active_weight in active if active_side == side
        )
        if same_side_weight > 0:
            return "position_pyramiding_not_allowed"

    if (
        position.max_open_signals_per_symbol is not None
        and len(active) >= position.max_open_signals_per_symbol
    ):
        return "position_open_signal_limit"
    if (
        position.max_open_position_weight_per_symbol is not None
        and open_weight + weight > position.max_open_position_weight_per_symbol
    ):
        return "position_open_weight_limit"
    return None
