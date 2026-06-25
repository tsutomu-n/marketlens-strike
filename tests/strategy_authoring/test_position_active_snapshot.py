from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sis.research.strategy_lab.authoring.compiler.position_active_snapshot import (
    _active_positions_at,
    _open_position_weight,
)


def _active(offset_minutes: int, side: str, weight: float):
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return (start + timedelta(minutes=offset_minutes), side, weight)


def test_active_positions_at_drops_expired_and_boundary_positions() -> None:
    ts_signal = datetime(2026, 1, 1, 0, 30, tzinfo=timezone.utc)
    active = [
        _active(10, "long", 0.2),
        _active(30, "short", 0.3),
        _active(31, "long", 0.4),
        _active(60, "short", 0.5),
    ]

    assert _active_positions_at(active, ts_signal) == [
        _active(31, "long", 0.4),
        _active(60, "short", 0.5),
    ]


def test_open_position_weight_sums_remaining_weights_without_side_netting() -> None:
    active = [
        _active(31, "long", 0.4),
        _active(60, "short", 0.5),
    ]

    assert _open_position_weight(active) == 0.9
