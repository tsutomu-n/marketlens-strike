from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sis.research.strategy_lab.authoring.compiler.temporal_block_reason import (
    _temporal_block_reason,
)
from sis.research.strategy_lab.authoring.contracts.risk_controls import TemporalRules


def test_temporal_block_reason_uses_schedule_before_state_limits() -> None:
    ts_signal = datetime(2026, 1, 1, 4, tzinfo=timezone.utc)
    row = {"ts_signal": ts_signal, "execution_symbol": "XYZ100"}
    temporal = TemporalRules(
        allowed_weekdays_utc=[4],
        allowed_hours_utc=[5],
        cooldown_minutes=60,
        max_signals_per_symbol_per_day=1,
    )

    assert (
        _temporal_block_reason(
            row,
            temporal,
            last_signal_by_symbol={"XYZ100": ts_signal},
            count_by_symbol_day={("XYZ100", ts_signal.date()): 1},
        )
        == "temporal_weekday_filter"
    )


def test_temporal_block_reason_checks_hour_after_weekday_passes() -> None:
    ts_signal = datetime(2026, 1, 1, 4, tzinfo=timezone.utc)

    assert (
        _temporal_block_reason(
            {"ts_signal": ts_signal, "execution_symbol": "XYZ100"},
            TemporalRules(allowed_weekdays_utc=[3], allowed_hours_utc=[5]),
            last_signal_by_symbol={},
            count_by_symbol_day={},
        )
        == "temporal_hour_filter"
    )


def test_temporal_block_reason_checks_cooldown_and_equal_boundary() -> None:
    ts_signal = datetime(2026, 1, 1, 4, tzinfo=timezone.utc)
    row = {"ts_signal": ts_signal, "execution_symbol": "XYZ100"}
    temporal = TemporalRules(cooldown_minutes=60)

    assert (
        _temporal_block_reason(
            row,
            temporal,
            last_signal_by_symbol={"XYZ100": ts_signal - timedelta(minutes=59)},
            count_by_symbol_day={},
        )
        == "temporal_cooldown"
    )
    assert (
        _temporal_block_reason(
            row,
            temporal,
            last_signal_by_symbol={"XYZ100": ts_signal - timedelta(minutes=60)},
            count_by_symbol_day={},
        )
        is None
    )


def test_temporal_block_reason_checks_daily_limit_after_cooldown_passes() -> None:
    ts_signal = datetime(2026, 1, 1, 4, tzinfo=timezone.utc)
    row = {"ts_signal": ts_signal, "execution_symbol": "XYZ100"}

    assert (
        _temporal_block_reason(
            row,
            TemporalRules(max_signals_per_symbol_per_day=2),
            last_signal_by_symbol={},
            count_by_symbol_day={("XYZ100", ts_signal.date()): 2},
        )
        == "temporal_symbol_daily_limit"
    )
