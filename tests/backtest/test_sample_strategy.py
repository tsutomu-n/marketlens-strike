from __future__ import annotations

from datetime import datetime, timezone

import polars as pl

from sis.backtest.trade_xyz.sample_strategies import sp500_breakout_signals


def test_sp500_breakout_signals_uses_close_as_signal_only() -> None:
    frame = pl.DataFrame(
        {
            "event_ts": [datetime(2026, 1, 1, hour, tzinfo=timezone.utc) for hour in range(5)],
            "symbol": ["SP500"] * 5,
            "close": [100.0, 101.0, 103.0, 102.0, 99.0],
        }
    )

    signals = sp500_breakout_signals(frame, entry_lookback=2, exit_lookback=2)

    assert signals.select(["event_ts", "signal"]).to_dicts() == [
        {"event_ts": datetime(2026, 1, 1, 2, tzinfo=timezone.utc), "signal": "entry"},
        {"event_ts": datetime(2026, 1, 1, 4, tzinfo=timezone.utc), "signal": "exit"},
    ]
    assert "fill_price" not in signals.columns
