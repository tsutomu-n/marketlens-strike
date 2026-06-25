from __future__ import annotations

from datetime import datetime
from typing import Any

from sis.research.strategy_lab.authoring.contracts.base import StrategyAuthoringValidationError


def _signal_timestamp(row: dict[str, Any]) -> datetime:
    value = row["ts_signal"]
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    raise StrategyAuthoringValidationError(f"Unsupported ts_signal value: {value!r}")
