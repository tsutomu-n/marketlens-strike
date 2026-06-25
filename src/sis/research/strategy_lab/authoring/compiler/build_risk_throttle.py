from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sis.research.strategy_lab.authoring.compiler.guard_block_reasons import (
    _feature_timestamp,
    _risk_throttle_block_reason,
)
from sis.research.strategy_lab.authoring.contracts.spec import StrategyAuthoringSpec


def _risk_throttle_block_for_row(
    *,
    row: dict[str, Any],
    spec: StrategyAuthoringSpec,
    symbol: str,
    cooldown_until_by_symbol: dict[str, datetime],
) -> str | None:
    ts_signal = _feature_timestamp(row)
    cooldown_until = cooldown_until_by_symbol.get(symbol)
    if cooldown_until is not None and ts_signal < cooldown_until:
        return "risk_throttle_cooldown"
    block_reason = _risk_throttle_block_reason(row, spec)
    if block_reason is not None and spec.rules.risk_throttle.cooldown_minutes is not None:
        cooldown_until_by_symbol[symbol] = ts_signal + timedelta(
            minutes=spec.rules.risk_throttle.cooldown_minutes
        )
    return block_reason
