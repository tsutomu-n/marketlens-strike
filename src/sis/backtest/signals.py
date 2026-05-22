from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import polars as pl

from sis.risk.scalping_policy import check_timeframe


@dataclass(frozen=True)
class ResearchSignal:
    ts_signal: datetime
    canonical_symbol: str
    side: str
    timeframe: str
    signal_strength: float | None = None


def _parse_timestamp(value: object) -> datetime:
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Signal ts_signal must be a non-empty ISO datetime")
    normalized = value.strip().replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError(f"Invalid signal ts_signal: {value}") from exc


def _parse_side(value: object) -> str:
    if not isinstance(value, str):
        raise ValueError("Signal side must be long or short")
    normalized = value.strip().lower()
    if normalized in {"buy", "bull", "long"}:
        return "long"
    if normalized in {"sell", "bear", "short"}:
        return "short"
    raise ValueError(f"Unsupported signal side: {value}")


def _parse_strength(value: object) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str) and value.strip():
        return float(value)
    return None


def load_research_signals(path: Path) -> list[ResearchSignal]:
    if not path.exists():
        return []
    frame = pl.read_csv(path)
    if frame.is_empty():
        return []

    required = {"ts_signal", "canonical_symbol", "side", "timeframe"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"Research signal CSV missing columns: {sorted(missing)}")

    signals: list[ResearchSignal] = []
    for row in frame.to_dicts():
        symbol = str(row["canonical_symbol"]).strip().upper()
        if not symbol:
            raise ValueError("Signal canonical_symbol must be non-empty")

        timeframe = str(row["timeframe"]).strip().lower()
        decision = check_timeframe(timeframe)
        if not decision.allowed:
            raise ValueError(f"{decision.reason}: {timeframe}")

        signals.append(
            ResearchSignal(
                ts_signal=_parse_timestamp(row["ts_signal"]),
                canonical_symbol=symbol,
                side=_parse_side(row["side"]),
                timeframe=timeframe,
                signal_strength=_parse_strength(row.get("signal_strength")),
            )
        )
    return sorted(signals, key=lambda item: item.ts_signal)
