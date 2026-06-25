from __future__ import annotations

from datetime import datetime

ActivePosition = tuple[datetime, str, float]


def _clamped_position_fraction(value: object, *, default: float = 1.0) -> float:
    if isinstance(value, int | float):
        return min(max(float(value), 0.0), 1.0)
    return default


def _non_negative_position_value(value: object, *, default: float) -> float:
    if isinstance(value, int | float):
        return max(float(value), 0.0)
    return default


def _compact_active_positions(active: list[ActivePosition], weight: float) -> list[ActivePosition]:
    if weight <= 0:
        return []
    end_at = max((item_end_at for item_end_at, _item_side, _item_weight in active), default=None)
    if end_at is None:
        return []
    sides = [item_side for _item_end_at, item_side, item_weight in active if item_weight > 0]
    side = sides[0] if sides else "long"
    return [(end_at, side, weight)]


def _reduce_active_side(
    active: list[ActivePosition], side: str, fraction: float
) -> list[ActivePosition]:
    total = sum(weight for _end_at, active_side, weight in active if active_side == side)
    to_reduce = total * _clamped_position_fraction(fraction)
    updated: list[ActivePosition] = []
    for end_at, active_side, weight in active:
        if active_side != side or to_reduce <= 0:
            updated.append((end_at, active_side, weight))
            continue
        reduced = min(weight, to_reduce)
        remaining = weight - reduced
        to_reduce -= reduced
        if remaining > 0:
            updated.append((end_at, active_side, remaining))
    return updated
