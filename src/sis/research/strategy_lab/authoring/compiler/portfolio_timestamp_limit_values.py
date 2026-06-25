from __future__ import annotations

import math
from typing import Any

from sis.research.strategy_lab.authoring.contracts.base import (
    StrategyAuthoringValidationError,
)


def _portfolio_timestamp_limit_value(
    rows: list[dict[str, Any]], *, value_key: str, field_name: str
) -> float | None:
    resolved: list[float] = []
    for row in rows:
        raw_value = row.get(value_key)
        value = float(raw_value) if isinstance(raw_value, int | float) else None
        if value is None:
            continue
        if value < 0:
            raise StrategyAuthoringValidationError(f"{field_name} must be >= 0")
        resolved.append(value)
    if not resolved:
        return None
    first = resolved[0]
    if any(not math.isclose(value, first, rel_tol=0.0, abs_tol=1e-12) for value in resolved[1:]):
        raise StrategyAuthoringValidationError(
            f"{field_name} must resolve to one value per timestamp"
        )
    return first
