from __future__ import annotations

from datetime import UTC, datetime, timedelta
import hashlib
import json
from pathlib import Path
import time
from typing import Any

import polars as pl

from sis.models import InstrumentSpec
from sis.storage.jsonl_store import read_json
from sis.storage.jsonl_store import write_json
from sis.venues.trade_xyz.client import TradeXyzClient
from sis.venues.trade_xyz.registry import load_trade_xyz_registry

SIGNAL_CANDLE_SCHEMA = {
    "schema_version": pl.Utf8,
    "ts_open": pl.Utf8,
    "ts_close": pl.Utf8,
    "canonical_symbol": pl.Utf8,
    "venue_symbol": pl.Utf8,
    "coin": pl.Utf8,
    "interval": pl.Utf8,
    "open": pl.Float64,
    "high": pl.Float64,
    "low": pl.Float64,
    "close": pl.Float64,
    "volume": pl.Float64,
    "trade_count": pl.Int64,
    "source": pl.Utf8,
    "source_time_open_ms": pl.Int64,
    "source_time_close_ms": pl.Int64,
    "raw_payload_sha256": pl.Utf8,
    "raw_payload_ref": pl.Utf8,
}


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _ms(value: datetime) -> int:
    item = value if value.tzinfo is not None else value.replace(tzinfo=UTC)
    return int(item.timestamp() * 1000)


def _from_ms(value: Any) -> str | None:
    parsed = _int_or_none(value)
    if parsed is None:
        return None
    return datetime.fromtimestamp(parsed / 1000, tz=UTC).isoformat()


def _float_or_none(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _int_or_none(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return None


def _payload_hash(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode(
        "utf-8"
    )
    return hashlib.sha256(encoded).hexdigest()


def _normalize_candle_row(
    *,
    instrument: InstrumentSpec,
    interval: str,
    row: dict[str, Any],
    raw_payload_ref: str,
) -> dict[str, Any]:
    ts_open = _from_ms(row.get("t"))
    ts_close = _from_ms(row.get("T"))
    return {
        "schema_version": "trade_xyz_signal_candle.v1",
        "ts_open": ts_open,
        "ts_close": ts_close,
        "canonical_symbol": instrument.canonical_symbol,
        "venue_symbol": instrument.venue_symbol,
        "coin": instrument.coin or f"xyz:{instrument.canonical_symbol}",
        "interval": str(row.get("i") or interval),
        "open": _float_or_none(row.get("o")),
        "high": _float_or_none(row.get("h")),
        "low": _float_or_none(row.get("l")),
        "close": _float_or_none(row.get("c")),
        "volume": _float_or_none(row.get("v")),
        "trade_count": _int_or_none(row.get("n")),
        "source": "hyperliquid_info_candleSnapshot",
        "source_time_open_ms": _int_or_none(row.get("t")),
        "source_time_close_ms": _int_or_none(row.get("T")),
        "raw_payload_sha256": _payload_hash(row),
        "raw_payload_ref": raw_payload_ref,
    }


def _active_instruments(
    registry_path: Path,
    *,
    symbols: list[str] | None,
) -> list[InstrumentSpec]:
    instruments = [
        item
        for item in load_trade_xyz_registry(registry_path)
        if item.venue.value == "trade_xyz" and item.active
    ]
    if symbols is None:
        return instruments
    requested = {item.strip().upper() for item in symbols if item.strip()}
    return [item for item in instruments if item.canonical_symbol.upper() in requested]


def _manifest_parquet_path(data_dir: Path, payload: dict[str, Any]) -> Path:
    artifacts = payload.get("artifacts") if isinstance(payload.get("artifacts"), dict) else {}
    value = artifacts.get("normalized_signal_candles")
    if isinstance(value, str) and value:
        path = Path(value)
        return path if path.is_absolute() else Path.cwd() / path
    return data_dir / "normalized/trade_xyz_signal_candles.parquet"


def _artifact_values(path: Path, column: str) -> set[str]:
    if not path.exists():
        return set()
    try:
        frame = pl.read_parquet(path, columns=[column])
    except (FileNotFoundError, pl.exceptions.PolarsError):
        return set()
    if column not in frame.columns:
        return set()
    return {str(item).strip() for item in frame.get_column(column).drop_nulls().unique().to_list()}


def signal_candles_manifest_is_fresh(
    *,
    data_dir: Path,
    symbols: list[str] | None = None,
    intervals: list[str] | None = None,
    max_age_hours: float = 24.0,
    now: datetime | None = None,
) -> tuple[bool, dict[str, Any]]:
    manifest_path = data_dir / "manifests/trade_xyz_signal_candles_manifest.json"
    if not manifest_path.exists():
        return False, {"reason": "missing_signal_candles_manifest"}
    payload = read_json(manifest_path)
    if not isinstance(payload, dict):
        return False, {"reason": "invalid_signal_candles_manifest"}
    if int(payload.get("request_error_count") or 0) > 0:
        return False, {"reason": "signal_candle_request_errors_present"}
    if int(payload.get("row_count") or 0) <= 0:
        return False, {"reason": "signal_candle_rows_empty"}

    artifact_path = _manifest_parquet_path(data_dir, payload)
    artifact_symbols = {
        item.upper() for item in _artifact_values(artifact_path, "canonical_symbol")
    }
    artifact_intervals = _artifact_values(artifact_path, "interval")

    requested_symbols = {item.strip().upper() for item in symbols or [] if item.strip()}
    if requested_symbols:
        available_symbols = artifact_symbols or {
            str(item).strip().upper() for item in payload.get("symbols", [])
        }
        missing_symbols = sorted(requested_symbols - available_symbols)
        if missing_symbols:
            return False, {"reason": "signal_candle_symbols_missing", "missing": missing_symbols}

    requested_intervals = {item.strip() for item in intervals or [] if item.strip()}
    if requested_intervals:
        available_intervals = artifact_intervals or {
            str(item).strip() for item in payload.get("intervals", [])
        }
        missing_intervals = sorted(requested_intervals - available_intervals)
        if missing_intervals:
            return False, {
                "reason": "signal_candle_intervals_missing",
                "missing": missing_intervals,
            }

    generated_at = payload.get("generated_at")
    if not isinstance(generated_at, str):
        return False, {"reason": "signal_candle_generated_at_missing"}
    try:
        generated = datetime.fromisoformat(generated_at)
    except ValueError:
        return False, {"reason": "signal_candle_generated_at_invalid"}
    generated = generated if generated.tzinfo is not None else generated.replace(tzinfo=UTC)
    reference_now = now or _utc_now()
    age_hours = max(0.0, (reference_now - generated).total_seconds() / 3600)
    if age_hours > max_age_hours:
        return False, {"reason": "signal_candle_manifest_stale", "age_hours": age_hours}
    return True, {
        "reason": "signal_candles_fresh",
        "age_hours": age_hours,
        "row_count": payload.get("row_count"),
        "symbol_count": payload.get("symbol_count"),
        "symbols": sorted(artifact_symbols) or payload.get("symbols", []),
        "intervals": sorted(artifact_intervals) or payload.get("intervals", []),
    }


def collect_trade_xyz_signal_candles(
    *,
    data_dir: Path,
    registry_path: Path | None = None,
    symbols: list[str] | None = None,
    intervals: list[str] | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
    period_days: int = 365,
    request_delay_seconds: float = 0.25,
    client: TradeXyzClient | None = None,
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    if period_days <= 0:
        raise ValueError("period_days must be > 0")
    if request_delay_seconds < 0:
        raise ValueError("request_delay_seconds must be >= 0")
    requested_intervals = intervals or ["30m", "4h", "1d", "3d"]
    if not requested_intervals:
        raise ValueError("at least one interval is required")

    generated = generated_at or _utc_now()
    effective_end = end or generated
    effective_start = start or (effective_end - timedelta(days=period_days))
    if effective_start >= effective_end:
        raise ValueError("start must be before end")

    effective_registry_path = (
        registry_path or data_dir / "registry/trade_xyz_instrument_registry.json"
    )
    instruments = _active_instruments(effective_registry_path, symbols=symbols)
    if not instruments:
        raise ValueError("no active trade_xyz instruments found for candle collection")

    own_client = client is None
    created_client = client or TradeXyzClient()
    rows: list[dict[str, Any]] = []
    request_errors: list[dict[str, Any]] = []
    raw_dir = data_dir / "raw/candles/trade_xyz"
    normalized_path = data_dir / "normalized/trade_xyz_signal_candles.parquet"
    try:
        for instrument in instruments:
            coin = instrument.coin or f"xyz:{instrument.canonical_symbol}"
            for interval in requested_intervals:
                try:
                    payload = created_client.candle_snapshot(
                        coin,
                        interval,
                        _ms(effective_start),
                        _ms(effective_end),
                    )
                except Exception as exc:
                    request_errors.append(
                        {
                            "canonical_symbol": instrument.canonical_symbol,
                            "coin": coin,
                            "interval": interval,
                            "error": f"{type(exc).__name__}: {exc}",
                        }
                    )
                    payload = []
                if request_delay_seconds > 0:
                    time.sleep(request_delay_seconds)
                raw_path = raw_dir / interval / f"{instrument.canonical_symbol}.json"
                raw_artifact = {
                    "schema_version": "trade_xyz_signal_candle_raw.v1",
                    "generated_at": generated.isoformat(),
                    "canonical_symbol": instrument.canonical_symbol,
                    "coin": coin,
                    "interval": interval,
                    "start_time_ms": _ms(effective_start),
                    "end_time_ms": _ms(effective_end),
                    "source": "hyperliquid_info_candleSnapshot",
                    "payload": payload,
                }
                write_json(raw_path, raw_artifact)
                for index, item in enumerate(payload):
                    if not isinstance(item, dict):
                        continue
                    rows.append(
                        _normalize_candle_row(
                            instrument=instrument,
                            interval=interval,
                            row=item,
                            raw_payload_ref=f"{raw_path}#payload[{index}]",
                        )
                    )
    finally:
        if own_client:
            created_client.close()

    new_frame = (
        pl.from_dicts(rows, schema=SIGNAL_CANDLE_SCHEMA, infer_schema_length=None)
        if rows
        else pl.DataFrame(schema=SIGNAL_CANDLE_SCHEMA)
    )
    frame = new_frame
    requested_symbols = {item.canonical_symbol for item in instruments}
    requested_interval_set = set(requested_intervals)
    if normalized_path.exists():
        existing = pl.read_parquet(normalized_path)
        if not existing.is_empty() and {"canonical_symbol", "interval"} <= set(existing.columns):
            kept = existing.filter(
                ~(
                    pl.col("canonical_symbol").is_in(sorted(requested_symbols))
                    & pl.col("interval").is_in(sorted(requested_interval_set))
                )
            )
            frame = pl.concat([kept, new_frame], how="diagonal_relaxed") if rows else kept
    normalized_path.parent.mkdir(parents=True, exist_ok=True)
    frame.sort(["canonical_symbol", "interval", "ts_open"]).write_parquet(normalized_path)

    artifact_intervals = (
        sorted(frame.get_column("interval").unique().to_list())
        if not frame.is_empty() and "interval" in frame.columns
        else []
    )
    artifact_symbols = (
        sorted(frame.get_column("canonical_symbol").unique().to_list())
        if not frame.is_empty() and "canonical_symbol" in frame.columns
        else []
    )
    manifest = {
        "schema_version": "trade_xyz_signal_candles_manifest.v1",
        "generated_at": generated.isoformat(),
        "data_dir": str(data_dir),
        "registry_path": str(effective_registry_path),
        "source": "hyperliquid_info_candleSnapshot",
        "start": effective_start.isoformat(),
        "end": effective_end.isoformat(),
        "period_days": period_days,
        "request_delay_seconds": request_delay_seconds,
        "intervals": artifact_intervals,
        "requested_intervals": requested_intervals,
        "symbols": artifact_symbols,
        "requested_symbols": sorted(requested_symbols),
        "row_count": frame.height,
        "new_row_count": len(rows),
        "symbol_count": len(artifact_symbols),
        "request_error_count": len(request_errors),
        "request_errors": request_errors,
        "artifacts": {
            "raw_candles_root": str(raw_dir),
            "normalized_signal_candles": str(normalized_path),
        },
        "notes": [
            "Signal candles are historical OHLCV inputs for strategy signals.",
            "Do not use these candles as fill snapshots; fill modeling uses quote snapshots.",
        ],
    }
    write_json(data_dir / "manifests/trade_xyz_signal_candles_manifest.json", manifest)
    return manifest
