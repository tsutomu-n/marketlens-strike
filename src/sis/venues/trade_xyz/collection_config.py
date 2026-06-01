from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


DEFAULT_COLLECTION_CONFIG_PATH = Path("configs/trade_xyz_data_collection.yaml")


@dataclass(frozen=True)
class TradeXyzDataCollectionConfig:
    symbols: tuple[str, ...]
    duration_minutes: int
    interval_seconds: int
    usable_start_date: str | None
    min_days: float
    max_gap_minutes: float
    max_oracle_lag_minutes: float
    traceable_only: bool
    collect_real_market_reference: bool
    collect_signal_candles: bool
    signal_candle_intervals: tuple[str, ...]
    signal_candle_period_days: int
    signal_candle_max_age_hours: float
    archive_coins: tuple[str, ...]
    archive_start_date: str | None


def _as_mapping(value: Any, *, name: str) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError(f"{name} must be a mapping")
    return value


def _as_str_tuple(value: Any, *, name: str, required: bool = True) -> tuple[str, ...]:
    if value is None:
        if required:
            raise ValueError(f"{name} is required")
        return ()
    if isinstance(value, str):
        items = [item.strip() for item in value.split(",") if item.strip()]
    elif isinstance(value, list):
        items = [str(item).strip() for item in value if str(item).strip()]
    else:
        raise ValueError(f"{name} must be a list or comma-separated string")
    if required and not items:
        raise ValueError(f"{name} must not be empty")
    return tuple(items)


def _positive_int(value: Any, *, name: str, default: int) -> int:
    item = default if value is None else int(value)
    if item <= 0:
        raise ValueError(f"{name} must be > 0")
    return item


def _positive_float(value: Any, *, name: str, default: float) -> float:
    item = default if value is None else float(value)
    if item <= 0:
        raise ValueError(f"{name} must be > 0")
    return item


def load_trade_xyz_data_collection_config(
    path: Path | None = None,
) -> TradeXyzDataCollectionConfig:
    config_path = path or DEFAULT_COLLECTION_CONFIG_PATH
    payload = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    root = _as_mapping(payload, name=str(config_path))
    quote = _as_mapping(root.get("quote_collection"), name="quote_collection")
    cutoff = _as_mapping(root.get("data_cutoff"), name="data_cutoff")
    readiness = _as_mapping(root.get("readiness"), name="readiness")
    reference = _as_mapping(root.get("reference_data"), name="reference_data")
    candles = _as_mapping(root.get("signal_candles"), name="signal_candles")
    archive = _as_mapping(root.get("historical_archive"), name="historical_archive")

    return TradeXyzDataCollectionConfig(
        symbols=tuple(item.upper() for item in _as_str_tuple(root.get("symbols"), name="symbols")),
        duration_minutes=_positive_int(
            quote.get("duration_minutes"), name="quote_collection.duration_minutes", default=1440
        ),
        interval_seconds=_positive_int(
            quote.get("interval_seconds"), name="quote_collection.interval_seconds", default=60
        ),
        usable_start_date=(
            str(cutoff["usable_start_date"]) if cutoff.get("usable_start_date") else None
        ),
        min_days=_positive_float(
            readiness.get("min_days"), name="readiness.min_days", default=30.0
        ),
        max_gap_minutes=_positive_float(
            readiness.get("max_gap_minutes"), name="readiness.max_gap_minutes", default=10.0
        ),
        max_oracle_lag_minutes=_positive_float(
            readiness.get("max_oracle_lag_minutes"),
            name="readiness.max_oracle_lag_minutes",
            default=90.0,
        ),
        traceable_only=bool(readiness.get("traceable_only", True)),
        collect_real_market_reference=bool(reference.get("collect_real_market_reference", True)),
        collect_signal_candles=bool(candles.get("collect", True)),
        signal_candle_intervals=_as_str_tuple(
            candles.get("intervals", ["30m", "4h", "1d", "3d"]),
            name="signal_candles.intervals",
        ),
        signal_candle_period_days=_positive_int(
            candles.get("period_days"), name="signal_candles.period_days", default=365
        ),
        signal_candle_max_age_hours=_positive_float(
            candles.get("max_age_hours"), name="signal_candles.max_age_hours", default=24.0
        ),
        archive_coins=_as_str_tuple(
            archive.get("coins"), name="historical_archive.coins", required=False
        ),
        archive_start_date=str(archive["start_date"]) if archive.get("start_date") else None,
    )


def join_csv(items: tuple[str, ...] | list[str]) -> str:
    return ",".join(items)
