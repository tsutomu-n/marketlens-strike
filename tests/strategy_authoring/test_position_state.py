from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sis.research.strategy_lab.authoring.compiler.position_state import (
    _clamped_position_fraction,
    _compact_active_positions,
    _non_negative_position_value,
    _reduce_active_side,
)


def test_compact_active_positions_keeps_latest_end_and_first_positive_side() -> None:
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    active = [
        (start + timedelta(hours=1), "short", 0.0),
        (start + timedelta(hours=2), "long", 0.4),
        (start + timedelta(hours=3), "short", 0.6),
    ]

    assert _compact_active_positions(active, 0.75) == [(start + timedelta(hours=3), "long", 0.75)]


def test_compact_active_positions_drops_zero_or_missing_weight() -> None:
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)

    assert _compact_active_positions([(start, "long", 1.0)], 0.0) == []
    assert _compact_active_positions([], 1.0) == []


def test_reduce_active_side_consumes_matching_side_in_order() -> None:
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    active = [
        (start + timedelta(hours=1), "long", 0.4),
        (start + timedelta(hours=2), "short", 0.5),
        (start + timedelta(hours=3), "long", 0.6),
    ]

    assert _reduce_active_side(active, "long", 0.5) == [
        (start + timedelta(hours=2), "short", 0.5),
        (start + timedelta(hours=3), "long", 0.5),
    ]


def test_position_fraction_helpers_preserve_existing_defaults() -> None:
    assert _clamped_position_fraction(-0.25) == 0.0
    assert _clamped_position_fraction(0.4) == 0.4
    assert _clamped_position_fraction(1.5) == 1.0
    assert _clamped_position_fraction("not numeric") == 1.0
    assert _clamped_position_fraction(None, default=0.5) == 0.5

    assert _non_negative_position_value(-0.25, default=1.0) == 0.0
    assert _non_negative_position_value(0.4, default=1.0) == 0.4
    assert _non_negative_position_value("not numeric", default=0.75) == 0.75
