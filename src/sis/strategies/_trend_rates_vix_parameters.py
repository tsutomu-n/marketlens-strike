from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class TrendRatesVixParameters:
    min_source_confidence: float | None = None
    max_vix_level: float | None = None
    min_research_return_1d: float | None = None
    timeframe: str = "4h"


def _single_grid_value(spec: Any, key: str) -> Any:
    grid = getattr(spec, "parameter_grid", None)
    if not isinstance(grid, dict):
        return None
    values = grid.get(key)
    if not isinstance(values, list) or not values:
        return None
    return values[0]


def _optional_float(spec: Any, *keys: str) -> float | None:
    for key in keys:
        value = _single_grid_value(spec, key)
        if value is None:
            continue
        return float(value)
    return None


def _timeframe(spec: Any) -> str:
    value = _single_grid_value(spec, "timeframe")
    if value is None:
        return "4h"
    text = str(value).strip()
    if not text:
        raise ValueError("parameter_grid.timeframe must be non-empty")
    return text


def trend_rates_vix_parameters(spec: Any) -> TrendRatesVixParameters:
    return TrendRatesVixParameters(
        min_source_confidence=_optional_float(spec, "min_source_confidence"),
        max_vix_level=_optional_float(spec, "max_vix_level", "vix_gate"),
        min_research_return_1d=_optional_float(spec, "min_research_return_1d"),
        timeframe=_timeframe(spec),
    )
