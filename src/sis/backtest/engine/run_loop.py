from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class BreakoutParameters:
    entry_lookback: int = 20
    exit_lookback: int = 10


def signal_kind(
    rows: list[dict[str, object]], index: int, breakout: BreakoutParameters
) -> str | None:
    close = rows[index].get("close")
    if not isinstance(close, int | float):
        return None
    if index >= breakout.entry_lookback:
        previous = [
            row.get("close")
            for row in rows[index - breakout.entry_lookback : index]
            if isinstance(row.get("close"), int | float)
        ]
        if previous and close > max(previous):
            return "entry"
    if index >= breakout.exit_lookback:
        previous = [
            row.get("close")
            for row in rows[index - breakout.exit_lookback : index]
            if isinstance(row.get("close"), int | float)
        ]
        if previous and close < min(previous):
            return "exit"
    return None


def row_event_ts(row: dict[str, object]) -> datetime:
    value = row["event_ts"]
    if not isinstance(value, datetime):
        raise ValueError(f"event_ts must be datetime, got {type(value).__name__}")
    return value


def row_index(row: dict[str, object]) -> int:
    value = row["_row_index"]
    if not isinstance(value, int):
        raise ValueError(f"_row_index must be int, got {type(value).__name__}")
    return value


def as_float_value(value: Any, *, field_name: str) -> float:
    if not isinstance(value, int | float):
        raise ValueError(f"{field_name} must be numeric")
    return float(value)


def optional_float(value: object) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None
