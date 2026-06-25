from __future__ import annotations

from typing import Any, Literal

from sis.research.strategy_lab.authoring.contracts.base import StrategyAuthoringValidationError


def _side_from_column(row: dict[str, Any], column: str) -> Literal["long", "short", "none"]:
    value = str(row.get(column) or "").strip().lower()
    if value in {"buy", "bull", "long"}:
        return "long"
    if value in {"sell", "bear", "short"}:
        return "short"
    if value in {"", "hold", "none", "skip", "flat"}:
        return "none"
    raise StrategyAuthoringValidationError(f"Unsupported side value in {column}: {value}")
