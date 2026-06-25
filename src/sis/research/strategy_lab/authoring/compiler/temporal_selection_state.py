from __future__ import annotations

from datetime import datetime
from typing import Any

from sis.research.strategy_lab.authoring.compiler.common import _signal_timestamp


def _record_temporal_selected_signal(
    row: dict[str, Any],
    *,
    last_signal_by_symbol: dict[str, datetime],
    count_by_symbol_day: dict[tuple[str, object], int],
) -> None:
    ts_signal = _signal_timestamp(row)
    symbol = str(row["execution_symbol"])
    last_signal_by_symbol[symbol] = ts_signal
    day_key = (symbol, ts_signal.date())
    count_by_symbol_day[day_key] = count_by_symbol_day.get(day_key, 0) + 1
