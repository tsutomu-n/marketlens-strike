from __future__ import annotations

from typing import Any


def _rank_score(raw_score: float | None) -> float | None:
    if raw_score is None:
        return None
    return max(0.0, min(1.0, raw_score))


def _tail_bucket(rank_score: float | None) -> str:
    if rank_score is None:
        return "none"
    if rank_score >= 0.8:
        return "top"
    if rank_score <= 0.2:
        return "bottom"
    return "middle"


def _score_value(row: dict[str, Any]) -> float | None:
    value = row.get("raw_score")
    return float(value) if isinstance(value, int | float) else None
