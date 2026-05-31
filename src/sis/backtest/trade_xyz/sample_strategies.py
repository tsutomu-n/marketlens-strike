from __future__ import annotations

import polars as pl


def sp500_breakout_signals(
    frame: pl.DataFrame, *, entry_lookback: int = 20, exit_lookback: int = 10
) -> pl.DataFrame:
    rows = frame.sort("event_ts").to_dicts()
    signals: list[dict[str, object]] = []
    for index, row in enumerate(rows):
        close = row.get("close")
        if not isinstance(close, int | float):
            continue
        if index >= entry_lookback:
            previous = [
                item.get("close")
                for item in rows[index - entry_lookback : index]
                if isinstance(item.get("close"), int | float)
            ]
            if previous and close > max(previous):
                signals.append(
                    {
                        "event_ts": row["event_ts"],
                        "symbol": "SP500",
                        "signal": "entry",
                        "reason": "close_breaks_previous_high",
                    }
                )
                continue
        if index >= exit_lookback:
            previous = [
                item.get("close")
                for item in rows[index - exit_lookback : index]
                if isinstance(item.get("close"), int | float)
            ]
            if previous and close < min(previous):
                signals.append(
                    {
                        "event_ts": row["event_ts"],
                        "symbol": "SP500",
                        "signal": "exit",
                        "reason": "close_breaks_previous_low",
                    }
                )
    schema = {
        "event_ts": pl.Datetime(time_zone="UTC"),
        "symbol": pl.Utf8,
        "signal": pl.Utf8,
        "reason": pl.Utf8,
    }
    if not signals:
        return pl.DataFrame(schema=schema)
    return pl.from_dicts(signals, schema=schema)
