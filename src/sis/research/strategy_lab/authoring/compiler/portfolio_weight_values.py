from __future__ import annotations

from typing import Any


def _position_weight_value(row: dict[str, Any]) -> float:
    value = row.get("position_weight")
    return float(value) if isinstance(value, int | float) else 1.0


def _portfolio_turnover_weight_value(row: dict[str, Any]) -> float:
    value = row.get("_portfolio_turnover_weight")
    if isinstance(value, int | float):
        return abs(float(value))
    return abs(_position_weight_value(row))
