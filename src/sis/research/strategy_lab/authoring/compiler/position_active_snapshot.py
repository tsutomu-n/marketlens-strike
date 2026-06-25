from __future__ import annotations

from datetime import datetime

from sis.research.strategy_lab.authoring.compiler.position_state import ActivePosition


def _active_positions_at(active: list[ActivePosition], ts_signal: datetime) -> list[ActivePosition]:
    return [
        (end_at, active_side, weight)
        for end_at, active_side, weight in active
        if end_at > ts_signal
    ]


def _open_position_weight(active: list[ActivePosition]) -> float:
    return sum(weight for _end_at, _active_side, weight in active)
