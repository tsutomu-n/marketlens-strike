from __future__ import annotations

from datetime import datetime, timezone

from sis.research.strategy_lab.authoring.compiler.temporal_selection_state import (
    _record_temporal_selected_signal,
)


def test_record_temporal_selected_signal_updates_last_signal_and_daily_count() -> None:
    last_signal_by_symbol: dict[str, datetime] = {}
    count_by_symbol_day: dict[tuple[str, object], int] = {}
    row = {
        "ts_signal": datetime(2026, 1, 1, 4, tzinfo=timezone.utc),
        "execution_symbol": "XYZ100",
    }

    _record_temporal_selected_signal(
        row,
        last_signal_by_symbol=last_signal_by_symbol,
        count_by_symbol_day=count_by_symbol_day,
    )

    assert last_signal_by_symbol == {"XYZ100": row["ts_signal"]}
    assert count_by_symbol_day == {("XYZ100", row["ts_signal"].date()): 1}


def test_record_temporal_selected_signal_increments_existing_daily_count() -> None:
    ts_signal = datetime(2026, 1, 1, 8, tzinfo=timezone.utc)
    last_signal_by_symbol = {"XYZ100": datetime(2026, 1, 1, 4, tzinfo=timezone.utc)}
    count_by_symbol_day: dict[tuple[str, object], int] = {("XYZ100", ts_signal.date()): 1}

    _record_temporal_selected_signal(
        {"ts_signal": ts_signal, "execution_symbol": "XYZ100"},
        last_signal_by_symbol=last_signal_by_symbol,
        count_by_symbol_day=count_by_symbol_day,
    )

    assert last_signal_by_symbol == {"XYZ100": ts_signal}
    assert count_by_symbol_day == {("XYZ100", ts_signal.date()): 2}
