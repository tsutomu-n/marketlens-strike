from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any

import polars as pl

from sis.crypto_perp.events import CryptoPerpEvent


TICKER_SOURCE_AVAILABLE = "available"
TICKER_SOURCE_MISSING_BEFORE_CUTOFF = "TICKER_SOURCE_MISSING_BEFORE_CUTOFF"
TICKER_SOURCE_STALE = "TICKER_SOURCE_STALE"
TICKER_MANIFEST_SCHEMA_VERSION = "crypto_perp_ticker_manifest.v1"
TICKER_ROWS_SCHEMA_VERSION = "ticker_rows.parquet"

_REQUIRED_TICKER_COLUMNS = frozenset(
    {
        "exchange",
        "market_type",
        "symbol_canonical",
        "ts_exchange_ms",
        "ts_received_ms",
        "source_channel",
        "coverage_class",
    }
)


@dataclass(frozen=True)
class TickerSourceStatus:
    row_count: int
    reason: str
    source_refs: list[dict[str, str]]
    metadata: dict[str, Any]


def build_ticker_source_status(
    *,
    event: CryptoPerpEvent,
    source_root: Path,
    max_staleness_seconds: int = 900,
) -> TickerSourceStatus:
    if max_staleness_seconds < 0:
        raise ValueError("max_staleness_seconds must be non-negative")
    root = source_root.expanduser()
    symbol = event.canonical_symbol.upper()
    cutoff_ms = int(event.information_cutoff_at.timestamp() * 1000)
    max_staleness_ms = max_staleness_seconds * 1000
    manifest_path = root / "data" / "ticker_manifest.json"
    manifest_metadata = _manifest_metadata(manifest_path, symbol)
    parquet_paths = _ticker_parquet_paths(root, symbol)
    if not parquet_paths:
        return TickerSourceStatus(
            row_count=0,
            reason=TICKER_SOURCE_MISSING_BEFORE_CUTOFF,
            source_refs=_manifest_refs(manifest_path),
            metadata=manifest_metadata,
        )

    rows = _read_symbol_rows(parquet_paths, symbol)
    if rows.is_empty():
        return TickerSourceStatus(
            row_count=0,
            reason=TICKER_SOURCE_MISSING_BEFORE_CUTOFF,
            source_refs=_manifest_refs(manifest_path),
            metadata=manifest_metadata,
        )

    eligible = rows.filter(pl.col("ts_received_ms") <= cutoff_ms)
    if eligible.is_empty():
        return TickerSourceStatus(
            row_count=0,
            reason=TICKER_SOURCE_MISSING_BEFORE_CUTOFF,
            source_refs=_manifest_refs(manifest_path),
            metadata=manifest_metadata,
        )

    selected = (
        eligible.sort(["ts_received_ms", "ts_exchange_ms"], descending=[True, True])
        .head(1)
        .row(0, named=True)
    )
    ts_received_ms = _required_int(selected, "ts_received_ms")
    staleness_ms = cutoff_ms - ts_received_ms
    metadata = {
        **manifest_metadata,
        **_selected_row_metadata(selected, cutoff_ms=cutoff_ms, manifest_path=manifest_path),
    }
    selected_parquet_path = Path(str(selected["__parquet_path"]))
    refs = [
        _local_file_source_ref(selected_parquet_path, TICKER_ROWS_SCHEMA_VERSION),
        *_manifest_refs(manifest_path),
    ]
    if staleness_ms > max_staleness_ms:
        return TickerSourceStatus(
            row_count=0,
            reason=TICKER_SOURCE_STALE,
            source_refs=refs,
            metadata=metadata,
        )
    return TickerSourceStatus(
        row_count=1,
        reason=TICKER_SOURCE_AVAILABLE,
        source_refs=refs,
        metadata=metadata,
    )


def _ticker_parquet_paths(source_root: Path, symbol: str) -> list[Path]:
    ticker_root = source_root / "data" / "ticker_rows"
    return sorted(ticker_root.glob(f"exchange=*/symbol={symbol}/date=*/ticker_rows.parquet"))


def _read_symbol_rows(parquet_paths: list[Path], symbol: str) -> pl.DataFrame:
    frames: list[pl.DataFrame] = []
    for path in parquet_paths:
        frame = pl.read_parquet(path)
        missing = sorted(_REQUIRED_TICKER_COLUMNS.difference(frame.columns))
        if missing:
            raise ValueError(f"ticker rows missing required columns {missing}: {path}")
        frames.append(
            frame.with_columns(
                pl.col("symbol_canonical").cast(pl.Utf8).str.to_uppercase(),
                pl.col("ts_received_ms").cast(pl.Int64),
                pl.col("ts_exchange_ms").cast(pl.Int64),
                pl.lit(path.as_posix()).alias("__parquet_path"),
            ).filter(pl.col("symbol_canonical") == symbol)
        )
    if not frames:
        return pl.DataFrame()
    return pl.concat(frames, how="vertical_relaxed")


def _selected_row_metadata(
    row: dict[str, Any],
    *,
    cutoff_ms: int,
    manifest_path: Path,
) -> dict[str, Any]:
    ts_received_ms = _required_int(row, "ts_received_ms")
    ts_exchange_ms = _optional_int(row.get("ts_exchange_ms"))
    selected_parquet_path = str(row["__parquet_path"])
    metadata: dict[str, Any] = {
        "ts_received_ms": ts_received_ms,
        "ts_exchange_ms": ts_exchange_ms,
        "staleness_seconds": (cutoff_ms - ts_received_ms) / 1000,
        "exchange": _optional_str(row.get("exchange")),
        "market_type": _optional_str(row.get("market_type")),
        "symbol_canonical": _optional_str(row.get("symbol_canonical")),
        "source_channel": _optional_str(row.get("source_channel")),
        "coverage_class": _optional_str(row.get("coverage_class")),
        "selected_parquet_path": selected_parquet_path,
    }
    if manifest_path.exists():
        metadata["manifest_path"] = manifest_path.as_posix()
    return metadata


def _manifest_metadata(manifest_path: Path, symbol: str) -> dict[str, Any]:
    if not manifest_path.exists():
        return {"symbol_canonical": symbol}
    payload = _json_object(manifest_path)
    schema_version = str(payload.get("schema_version", ""))
    if schema_version != TICKER_MANIFEST_SCHEMA_VERSION:
        raise ValueError(
            f"ticker manifest schema_version must be {TICKER_MANIFEST_SCHEMA_VERSION}: "
            f"{manifest_path}"
        )
    for field in ("credentials_used", "exchange_write_used", "live_order_submitted"):
        if payload.get(field) is not False:
            raise ValueError(f"ticker manifest {field} must be false: {manifest_path}")
    metadata: dict[str, Any] = {
        "manifest_path": manifest_path.as_posix(),
        "symbol_canonical": symbol,
    }
    for key in ("exchange", "market_type", "coverage_class"):
        if key in payload:
            metadata[key] = str(payload[key])
    return metadata


def _manifest_refs(manifest_path: Path) -> list[dict[str, str]]:
    if not manifest_path.exists():
        return []
    return [_local_file_source_ref(manifest_path, TICKER_MANIFEST_SCHEMA_VERSION)]


def _local_file_source_ref(path: Path, schema_version: str) -> dict[str, str]:
    return {
        "path": path.as_posix(),
        "sha256": "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest(),
        "schema_version": schema_version,
    }


def _json_object(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def _required_int(row: dict[str, Any], key: str) -> int:
    value = _optional_int(row.get(key))
    if value is None:
        raise ValueError(f"ticker row {key} must be an integer")
    return value


def _optional_int(value: object) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, (float, str)):
        return int(value)
    return None


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    return str(value)
