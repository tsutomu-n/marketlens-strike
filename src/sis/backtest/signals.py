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
    stop_loss_bps: float | None = None
    take_profit_bps: float | None = None
    trailing_stop_bps: float | None = None
    partial_take_profit_bps: float | None = None
    partial_exit_fraction: float | None = None
    min_holding_minutes: int | None = None
    exit_on_opposite_signal: bool = False
    exit_on_close_signal: bool = False
    exit_on_reduce_signal: bool = False
    reduce_fraction: float | None = None
    exit_on_add_signal: bool = False
    add_fraction: float | None = None
    exit_on_rebalance_signal: bool = False
    rebalance_target_fraction: float | None = None
    bracket_type: str = "none"
    bracket_time_stop_minutes: int | None = None
    bracket_break_even_after_bps: float | None = None
    entry_order_type: str = "market"
    entry_limit_offset_bps: float | None = None
    entry_stop_offset_bps: float | None = None
    entry_timeout_minutes: int | None = None
    slippage_bps: float = 0.0
    max_fill_fraction: float = 1.0
    max_spread_bps: float | None = None
    min_depth_usd: float | None = None
    depth_column: str | None = None
    depth_participation_rate: float = 1.0
    position_weight: float = 1.0
    notional_usd: float | None = None


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
        raise ValueError("Signal side must be long, short, close, reduce, add, or rebalance")
    normalized = value.strip().lower()
    if normalized in {"buy", "bull", "long"}:
        return "long"
    if normalized in {"sell", "bear", "short"}:
        return "short"
    if normalized in {"close", "exit", "flat"}:
        return "close"
    if normalized in {"reduce", "trim", "scale_out"}:
        return "reduce"
    if normalized in {"add", "scale_in", "pyramid"}:
        return "add"
    if normalized in {"rebalance", "resize", "target"}:
        return "rebalance"
    raise ValueError(f"Unsupported signal side: {value}")


def _parse_strength(value: object) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str) and value.strip():
        return float(value)
    return None


def _parse_optional_positive_float(value: object, *, field_name: str) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, int | float | str):
        parsed = float(value)
    else:
        raise ValueError(f"{field_name} must be a number")
    if parsed < 0:
        raise ValueError(f"{field_name} must be >= 0")
    return parsed


def _parse_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if value is None or value == "":
        return False
    if isinstance(value, int | float):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "y"}:
            return True
        if normalized in {"0", "false", "no", "n"}:
            return False
    raise ValueError(f"Unsupported boolean value: {value}")


def _parse_entry_order_type(value: object) -> str:
    normalized = str(value or "market").strip().lower()
    if normalized in {"market", "limit", "stop_market"}:
        return normalized
    raise ValueError(f"Unsupported entry_order_type: {value}")


def _parse_bracket_type(value: object) -> str:
    normalized = str(value or "none").strip().lower()
    if normalized in {"none", "oco"}:
        return normalized
    raise ValueError(f"Unsupported bracket_type: {value}")


def _parse_optional_positive_int(value: object, *, field_name: str) -> int | None:
    if value is None or value == "":
        return None
    parsed = int(value) if isinstance(value, int | float | str) else None
    if parsed is None:
        raise ValueError(f"{field_name} must be an integer")
    if parsed < 0:
        raise ValueError(f"{field_name} must be >= 0")
    return parsed


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
                stop_loss_bps=_parse_optional_positive_float(
                    row.get("stop_loss_bps"), field_name="stop_loss_bps"
                ),
                take_profit_bps=_parse_optional_positive_float(
                    row.get("take_profit_bps"), field_name="take_profit_bps"
                ),
                trailing_stop_bps=_parse_optional_positive_float(
                    row.get("trailing_stop_bps"), field_name="trailing_stop_bps"
                ),
                partial_take_profit_bps=_parse_optional_positive_float(
                    row.get("partial_take_profit_bps"), field_name="partial_take_profit_bps"
                ),
                partial_exit_fraction=_parse_optional_positive_float(
                    row.get("partial_exit_fraction"), field_name="partial_exit_fraction"
                ),
                min_holding_minutes=_parse_optional_positive_int(
                    row.get("min_holding_minutes"), field_name="min_holding_minutes"
                ),
                exit_on_opposite_signal=_parse_bool(row.get("exit_on_opposite_signal")),
                exit_on_close_signal=_parse_bool(row.get("exit_on_close_signal")),
                exit_on_reduce_signal=_parse_bool(row.get("exit_on_reduce_signal")),
                reduce_fraction=_parse_optional_positive_float(
                    row.get("reduce_fraction"), field_name="reduce_fraction"
                ),
                exit_on_add_signal=_parse_bool(row.get("exit_on_add_signal")),
                add_fraction=_parse_optional_positive_float(
                    row.get("add_fraction"), field_name="add_fraction"
                ),
                exit_on_rebalance_signal=_parse_bool(row.get("exit_on_rebalance_signal")),
                rebalance_target_fraction=_parse_optional_positive_float(
                    row.get("rebalance_target_fraction"),
                    field_name="rebalance_target_fraction",
                ),
                bracket_type=_parse_bracket_type(row.get("bracket_type")),
                bracket_time_stop_minutes=_parse_optional_positive_int(
                    row.get("bracket_time_stop_minutes"), field_name="bracket_time_stop_minutes"
                ),
                bracket_break_even_after_bps=_parse_optional_positive_float(
                    row.get("bracket_break_even_after_bps"),
                    field_name="bracket_break_even_after_bps",
                ),
                entry_order_type=_parse_entry_order_type(row.get("entry_order_type")),
                entry_limit_offset_bps=_parse_optional_positive_float(
                    row.get("entry_limit_offset_bps"), field_name="entry_limit_offset_bps"
                ),
                entry_stop_offset_bps=_parse_optional_positive_float(
                    row.get("entry_stop_offset_bps"), field_name="entry_stop_offset_bps"
                ),
                entry_timeout_minutes=_parse_optional_positive_int(
                    row.get("entry_timeout_minutes"), field_name="entry_timeout_minutes"
                ),
                slippage_bps=_parse_optional_positive_float(
                    row.get("slippage_bps"), field_name="slippage_bps"
                )
                or 0.0,
                max_fill_fraction=_parse_optional_positive_float(
                    row.get("max_fill_fraction"), field_name="max_fill_fraction"
                )
                or 1.0,
                max_spread_bps=_parse_optional_positive_float(
                    row.get("max_spread_bps"), field_name="max_spread_bps"
                ),
                min_depth_usd=_parse_optional_positive_float(
                    row.get("min_depth_usd"), field_name="min_depth_usd"
                ),
                depth_column=(
                    str(row.get("depth_column")).strip() if row.get("depth_column") else None
                ),
                depth_participation_rate=_parse_optional_positive_float(
                    row.get("depth_participation_rate"), field_name="depth_participation_rate"
                )
                or 1.0,
                position_weight=_parse_optional_positive_float(
                    row.get("position_weight"), field_name="position_weight"
                )
                or 1.0,
                notional_usd=_parse_optional_positive_float(
                    row.get("notional_usd"), field_name="notional_usd"
                ),
            )
        )
    return sorted(signals, key=lambda item: item.ts_signal)
