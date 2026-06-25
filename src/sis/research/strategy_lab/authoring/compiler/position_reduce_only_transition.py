from __future__ import annotations

from typing import Any

from sis.research.strategy_lab.authoring.compiler.position_state import (
    ActivePosition,
    _clamped_position_fraction,
    _reduce_active_side,
)
from sis.research.strategy_lab.authoring.compiler.signal_ids import _compiled_signal_id
from sis.research.strategy_lab.authoring.compiler.trade_blocking import _block_trade_row
from sis.research.strategy_lab.authoring.contracts.spec import StrategyAuthoringSpec


def _apply_reduce_only_entry_transition(
    *,
    row: dict[str, Any],
    spec: StrategyAuthoringSpec,
    active: list[ActivePosition],
    side: str,
) -> tuple[dict[str, Any], list[ActivePosition]]:
    opposing_side = "short" if side == "long" else "long"
    opposing_weight = sum(
        active_weight
        for _end_at, active_side, active_weight in active
        if active_side == opposing_side
    )
    if opposing_weight <= 0:
        return (
            _block_trade_row(
                row, spec=spec, block_reason="position_reduce_only_without_opposing_open"
            ),
            active,
        )
    fraction = _clamped_position_fraction(row.get("reduce_fraction"))
    reduce_row = dict(row)
    reduce_row["side"] = "reduce"
    reduce_row["signal_id"] = _compiled_signal_id(spec, reduce_row, side="reduce")
    reduce_row["position_weight"] = 0.0
    reduce_row["notional_usd"] = None
    reduce_row["reason_codes"] = [*list(row.get("reason_codes") or []), "reduce_only"]
    return reduce_row, _reduce_active_side(active, opposing_side, fraction)
