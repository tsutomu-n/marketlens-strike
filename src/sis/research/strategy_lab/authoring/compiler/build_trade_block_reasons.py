from __future__ import annotations

from datetime import datetime
from typing import Any

from sis.research.strategy_lab.authoring.compiler.build_risk_throttle import (
    _risk_throttle_block_for_row,
)
from sis.research.strategy_lab.authoring.compiler.guard_block_reasons import (
    _data_guard_block_reason,
    _event_window_block_reason,
)
from sis.research.strategy_lab.authoring.contracts.spec import StrategyAuthoringSpec


def _trade_block_reason_for_row(
    *,
    row: dict[str, Any],
    spec: StrategyAuthoringSpec,
    symbol: str,
    cooldown_until_by_symbol: dict[str, datetime],
) -> str | None:
    event_block_reason = _event_window_block_reason(row, spec)
    if event_block_reason is not None:
        return event_block_reason
    data_guard_block_reason = _data_guard_block_reason(row, spec)
    if data_guard_block_reason is not None:
        return data_guard_block_reason
    return _risk_throttle_block_for_row(
        row=row,
        spec=spec,
        symbol=symbol,
        cooldown_until_by_symbol=cooldown_until_by_symbol,
    )
