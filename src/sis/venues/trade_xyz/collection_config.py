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
    ws_enabled: bool
    ws_url: str
    ws_default_subscriptions: tuple[str, ...]
    ws_duration_minutes: int
    ws_heartbeat_seconds: int
    ws_server_timeout_seconds: int
    ws_reconnect_max_attempts: int
    ws_reconnect_initial_delay_seconds: float
    ws_reconnect_max_delay_seconds: float
    ws_output_root: str
    ws_write_control_messages: bool


_ALLOWED_WS_SUBSCRIPTIONS = {
    "bbo",
    "trades",
    "activeAssetCtx",
    "l2Book",
    "allMids",
}


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
    websocket = _as_mapping(root.get("websocket_collection"), name="websocket_collection")
    ws_reconnect = _as_mapping(websocket.get("reconnect"), name="websocket_collection.reconnect")
    ws_subscriptions = _as_str_tuple(
        websocket.get("default_subscriptions", ["bbo", "trades", "activeAssetCtx"]),
        name="websocket_collection.default_subscriptions",
    )
    invalid_ws_subscriptions = [
        item for item in ws_subscriptions if item not in _ALLOWED_WS_SUBSCRIPTIONS
    ]
    if invalid_ws_subscriptions:
        raise ValueError(
            "websocket_collection.default_subscriptions contains unsupported values: "
            + ",".join(invalid_ws_subscriptions)
        )

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
        ws_enabled=bool(websocket.get("enabled", False)),
        ws_url=str(websocket.get("ws_url") or "wss://api.hyperliquid.xyz/ws"),
        ws_default_subscriptions=ws_subscriptions,
        ws_duration_minutes=_positive_int(
            websocket.get("duration_minutes"),
            name="websocket_collection.duration_minutes",
            default=60,
        ),
        ws_heartbeat_seconds=_positive_int(
            websocket.get("heartbeat_seconds"),
            name="websocket_collection.heartbeat_seconds",
            default=30,
        ),
        ws_server_timeout_seconds=_positive_int(
            websocket.get("server_timeout_seconds"),
            name="websocket_collection.server_timeout_seconds",
            default=60,
        ),
        ws_reconnect_max_attempts=_positive_int(
            ws_reconnect.get("max_attempts"),
            name="websocket_collection.reconnect.max_attempts",
            default=5,
        ),
        ws_reconnect_initial_delay_seconds=_positive_float(
            ws_reconnect.get("initial_delay_seconds"),
            name="websocket_collection.reconnect.initial_delay_seconds",
            default=1.0,
        ),
        ws_reconnect_max_delay_seconds=_positive_float(
            ws_reconnect.get("max_delay_seconds"),
            name="websocket_collection.reconnect.max_delay_seconds",
            default=30.0,
        ),
        ws_output_root=str(websocket.get("output_root") or "raw/ws/trade_xyz"),
        ws_write_control_messages=bool(websocket.get("write_control_messages", True)),
    )


def join_csv(items: tuple[str, ...] | list[str]) -> str:
    return ",".join(items)
