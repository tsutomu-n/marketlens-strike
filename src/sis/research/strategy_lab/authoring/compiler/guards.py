from __future__ import annotations

from datetime import datetime
from typing import Any

from sis.research.strategy_lab.authoring.compiler.reward_risk_gate import (
    _apply_reward_risk_gate as _apply_reward_risk_gate,
)
from sis.research.strategy_lab.authoring.compiler.stop_target_width import (
    _apply_stop_target_width_gate as _apply_stop_target_width_gate,
)
from sis.research.strategy_lab.authoring.compiler.temporal_block_reason import (
    _temporal_block_reason,
)
from sis.research.strategy_lab.authoring.compiler.temporal_selection_state import (
    _record_temporal_selected_signal,
)
from sis.research.strategy_lab.authoring.compiler.trade_blocking import _block_trade_row
from sis.research.strategy_lab.authoring.contracts.spec import StrategyAuthoringSpec


def _apply_temporal_selection(
    rows: list[dict[str, Any]], spec: StrategyAuthoringSpec
) -> list[dict[str, Any]]:
    if not spec.rules.temporal.enabled:
        return rows

    last_signal_by_symbol: dict[str, datetime] = {}
    count_by_symbol_day: dict[tuple[str, object], int] = {}
    selected: list[dict[str, Any]] = []
    for row in sorted(rows, key=lambda item: (item["ts_signal"], item["signal_id"])):
        if row.get("side") == "none":
            selected.append(row)
            continue
        reason = _temporal_block_reason(
            row,
            spec.rules.temporal,
            last_signal_by_symbol=last_signal_by_symbol,
            count_by_symbol_day=count_by_symbol_day,
        )
        if reason is not None:
            selected.append(_block_trade_row(row, spec=spec, block_reason=reason))
            continue

        _record_temporal_selected_signal(
            row,
            last_signal_by_symbol=last_signal_by_symbol,
            count_by_symbol_day=count_by_symbol_day,
        )
        selected.append(row)
    return selected
