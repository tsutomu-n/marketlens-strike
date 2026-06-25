from __future__ import annotations

from datetime import datetime
from typing import Any

from sis.research.strategy_lab.authoring.compiler.position_active_snapshot import (
    _active_positions_at,
    _open_position_weight,
)
from sis.research.strategy_lab.authoring.compiler.position_row_state import (
    _apply_position_row_state,
)
from sis.research.strategy_lab.authoring.compiler.position_state_enabled import (
    _position_state_limits_enabled,
)
from sis.research.strategy_lab.authoring.compiler.signal_timestamps import _signal_timestamp
from sis.research.strategy_lab.authoring.contracts.spec import StrategyAuthoringSpec


def _apply_position_state_limits(
    rows: list[dict[str, Any]], spec: StrategyAuthoringSpec
) -> list[dict[str, Any]]:
    position = spec.rules.position
    if not _position_state_limits_enabled(spec):
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
        active = _active_positions_at(active_by_symbol.get(symbol, []), ts_signal)
        active_by_symbol[symbol] = active
        open_weight = _open_position_weight(active)

        result = _apply_position_row_state(
            row=row,
            spec=spec,
            active=active,
            open_weight=open_weight,
            ts_signal=ts_signal,
            horizon_minutes=horizon_minutes,
        )
        active_by_symbol[symbol] = result.active
        selected.append(result.selected_row)
    return selected
