from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sis.research.strategy_lab.authoring.compiler.common import (
    _block_trade_row,
    _position_weight_value,
    _signal_timestamp,
)
from sis.research.strategy_lab.authoring.compiler.position_entry_limits import (
    _position_entry_limit_block_reason,
)
from sis.research.strategy_lab.authoring.compiler.position_marker_transition import (
    _apply_position_marker_transition,
)
from sis.research.strategy_lab.authoring.compiler.position_reduce_only_transition import (
    _apply_reduce_only_entry_transition,
)
from sis.research.strategy_lab.authoring.contracts.spec import StrategyAuthoringSpec


def _apply_position_state_limits(
    rows: list[dict[str, Any]], spec: StrategyAuthoringSpec
) -> list[dict[str, Any]]:
    position = spec.rules.position
    if (
        not position.enabled
        and not spec.rules.order.reduce_only
        and spec.rules.order.reduce_only_column is None
    ):
        return rows

    horizon_minutes = position.holding_horizon_minutes or spec.backtest.label_horizon_minutes
    active_by_symbol: dict[str, list[tuple[datetime, str, float]]] = {}
    selected: list[dict[str, Any]] = []

    for row in sorted(rows, key=lambda item: (item["ts_signal"], item["signal_id"])):
        if row.get("side") == "none":
            selected.append(row)
            continue

        ts_signal = _signal_timestamp(row)
        symbol = str(row["execution_symbol"])
        active = [
            (end_at, active_side, weight)
            for end_at, active_side, weight in active_by_symbol.get(symbol, [])
            if end_at > ts_signal
        ]
        active_by_symbol[symbol] = active
        open_weight = sum(weight for _end_at, _active_side, weight in active)
        side = str(row.get("side") or "")

        if side in {"close", "reduce", "add", "rebalance"}:
            selected_row, updated_active = _apply_position_marker_transition(
                row=row,
                spec=spec,
                active=active,
                open_weight=open_weight,
            )
            active_by_symbol[symbol] = updated_active
            selected.append(selected_row)
            continue

        weight = abs(_position_weight_value(row))
        if row.get("entry_reduce_only") and side in {"long", "short"}:
            selected_row, updated_active = _apply_reduce_only_entry_transition(
                row=row,
                spec=spec,
                active=active,
                side=side,
            )
            active_by_symbol[symbol] = updated_active
            selected.append(selected_row)
            continue

        block_reason = _position_entry_limit_block_reason(
            position=position,
            active=active,
            open_weight=open_weight,
            side=side,
            weight=weight,
        )
        if block_reason is not None:
            selected.append(_block_trade_row(row, spec=spec, block_reason=block_reason))
            continue

        active.append((ts_signal + timedelta(minutes=horizon_minutes), side, weight))
        active_by_symbol[symbol] = active
        selected.append(row)
    return selected
