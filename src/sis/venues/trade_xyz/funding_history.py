from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
from typing import Any

import polars as pl

from sis.storage.jsonl_store import write_json
from sis.storage.normalize import collect_quote_logs
from sis.venues.trade_xyz.client import TradeXyzClient
from sis.venues.trade_xyz.registry import load_trade_xyz_registry


FUNDING_INTERVAL_MINUTES = 60

_FUNDING_EVENT_SCHEMA = {
    "schema_version": pl.Utf8,
    "funding_event_ts": pl.Utf8,
    "canonical_symbol": pl.Utf8,
    "venue_symbol": pl.Utf8,
    "funding_rate": pl.Float64,
    "funding_interval_minutes": pl.Int64,
    "oracle_price_at_funding": pl.Float64,
    "premium": pl.Float64,
    "impact_bid_px": pl.Float64,
    "impact_ask_px": pl.Float64,
    "impact_notional_usd": pl.Float64,
    "source_ts_ms": pl.Int64,
    "recv_ts_ms": pl.Int64,
    "raw_payload_sha256": pl.Utf8,
    "raw_payload_ref": pl.Utf8,
    "source": pl.Utf8,
    "funding_history_raw_payload_ref": pl.Utf8,
    "oracle_raw_payload_ref": pl.Utf8,
    "oracle_join_lag_seconds": pl.Float64,
    "oracle_join_ts_source": pl.Utf8,
    "notes": pl.List(pl.Utf8),
}


def _payload_hash(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _to_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return None


def _iso_from_ms(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, tz=UTC).isoformat()


def _ms_from_datetime(value: datetime) -> int:
    item = value if value.tzinfo is not None else value.replace(tzinfo=UTC)
    return int(item.timestamp() * 1000)


def _ms_from_event_ts(value: Any) -> int | None:
    if isinstance(value, datetime):
        return _ms_from_datetime(value)
    if isinstance(value, str):
        try:
            return _ms_from_datetime(datetime.fromisoformat(value.replace("Z", "+00:00")))
        except ValueError:
            return None
    return None


def _write_jsonl(rows: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, default=str) + "\n" for row in rows),
        encoding="utf-8",
    )


def _write_parquet(rows: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame = pl.from_dicts(rows, infer_schema_length=None) if rows else pl.DataFrame()
    frame.write_parquet(path)


def _write_funding_events_parquet(rows: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame = (
        pl.from_dicts(rows, schema=_FUNDING_EVENT_SCHEMA, infer_schema_length=None)
        if rows
        else pl.DataFrame(schema=_FUNDING_EVENT_SCHEMA)
    )
    frame.write_parquet(path)


def collect_trade_xyz_funding_history(
    *,
    data_dir: Path,
    registry_path: Path | None = None,
    symbols: list[str] | None = None,
    start_time_ms: int,
    end_time_ms: int | None = None,
    client: TradeXyzClient | None = None,
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    effective_registry_path = (
        registry_path or data_dir / "registry/trade_xyz_instrument_registry.json"
    )
    instruments = [
        item
        for item in load_trade_xyz_registry(effective_registry_path)
        if item.venue.value == "trade_xyz" and item.active
    ]
    requested_symbols = [item.upper() for item in symbols] if symbols else None
    if requested_symbols is not None:
        instruments = [
            item for item in instruments if item.canonical_symbol.upper() in requested_symbols
        ]
    if not instruments:
        raise ValueError("no active trade_xyz instruments matched funding history request")

    own_client = client is None
    created_client = client or TradeXyzClient()
    rows: list[dict[str, Any]] = []
    request_errors: dict[str, str] = {}
    try:
        for instrument in instruments:
            coin = instrument.coin or f"xyz:{instrument.canonical_symbol}"
            try:
                history_rows = created_client.funding_history(
                    coin, start_time_ms=start_time_ms, end_time_ms=end_time_ms
                )
            except Exception as exc:
                request_errors[instrument.canonical_symbol] = f"{type(exc).__name__}: {exc}"
                continue
            for index, payload in enumerate(history_rows):
                event_ms = _to_int(payload.get("time"))
                funding_rate = _to_float(payload.get("fundingRate") or payload.get("funding_rate"))
                if event_ms is None or funding_rate is None:
                    continue
                raw_hash = _payload_hash(payload)
                raw_ref = (
                    f"data/raw/funding_history/trade_xyz/"
                    f"{(generated_at or datetime.now(UTC)).date().isoformat()}.jsonl"
                    f"#symbol={instrument.canonical_symbol}#row={index}"
                )
                rows.append(
                    {
                        "schema_version": "funding_history_event.v1",
                        "funding_event_ts": _iso_from_ms(event_ms),
                        "canonical_symbol": instrument.canonical_symbol,
                        "venue_symbol": instrument.venue_symbol,
                        "coin": coin,
                        "funding_rate": funding_rate,
                        "premium": _to_float(payload.get("premium")),
                        "source_time_ms": event_ms,
                        "source": "hyperliquid_info.fundingHistory",
                        "oracle_price_at_funding": None,
                        "usable_as_backtest_funding_event": False,
                        "raw_payload_sha256": raw_hash,
                        "raw_payload_ref": raw_ref,
                        "raw_payload": payload,
                    }
                )
    finally:
        if own_client:
            created_client.close()

    generated = generated_at or datetime.now(UTC)
    raw_path = data_dir / f"raw/funding_history/trade_xyz/{generated.date().isoformat()}.jsonl"
    parquet_path = data_dir / "normalized/funding_history_events.parquet"
    manifest_path = data_dir / "manifests/funding_history_manifest.json"
    raw_rows = [dict(row) for row in rows]
    _write_jsonl(raw_rows, raw_path)
    normalized_rows = []
    for row in rows:
        item = dict(row)
        item.pop("raw_payload", None)
        item["raw_payload_ref"] = str(raw_path) + item["raw_payload_ref"].split(".jsonl", 1)[1]
        normalized_rows.append(item)
    _write_parquet(normalized_rows, parquet_path)

    manifest = {
        "schema_version": "funding_history_manifest.v1",
        "generated_at": generated.isoformat(),
        "registry_path": str(effective_registry_path),
        "raw_artifact_path": str(raw_path),
        "artifact_path": str(parquet_path),
        "start_time_ms": start_time_ms,
        "end_time_ms": end_time_ms,
        "requested_symbols": [item.canonical_symbol for item in instruments],
        "row_count": len(normalized_rows),
        "request_errors": request_errors,
        "source": "hyperliquid_info.fundingHistory",
        "source_docs": "https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/info-endpoint/perpetuals",
        "usable_as_backtest_funding_event": False,
        "not_directly_usable_reasons": [
            "fundingHistory provides fundingRate/premium/time but not oracle_price_at_funding",
            "run_backtest funding payments require oracle_price_at_funding",
        ],
    }
    write_json(manifest_path, manifest)
    return manifest


def _quote_match_ts_ms(log: Any) -> tuple[int, str] | None:
    oracle_ts_ms = _to_int(getattr(log, "oracle_ts_ms", None))
    if oracle_ts_ms is not None:
        return oracle_ts_ms, "oracle_ts_ms"
    source_ts_ms = _to_int(getattr(log, "source_ts_ms", None))
    if source_ts_ms is not None:
        return source_ts_ms, "source_ts_ms"
    recv_ts_ms = _to_int(getattr(log, "recv_ts_ms", None))
    if recv_ts_ms is not None:
        return recv_ts_ms, "recv_ts_ms"
    return _ms_from_datetime(log.ts_client), "ts_client"


def _nearest_oracle_quote(
    quotes: list[dict[str, Any]], *, event_ms: int, max_lag_ms: int
) -> dict[str, Any] | None:
    best: dict[str, Any] | None = None
    best_lag: int | None = None
    for item in quotes:
        lag = abs(int(item["match_ts_ms"]) - event_ms)
        if lag > max_lag_ms:
            continue
        if best_lag is None or lag < best_lag:
            best = item
            best_lag = lag
    return best


def build_trade_xyz_backtest_funding_events_from_history(
    *,
    data_dir: Path,
    funding_history_path: Path | None = None,
    raw_quotes_root: Path | None = None,
    max_oracle_lag_minutes: float = 90.0,
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    effective_generated_at = generated_at or datetime.now(UTC)
    effective_funding_history_path = (
        funding_history_path or data_dir / "normalized/funding_history_events.parquet"
    )
    effective_raw_quotes_root = raw_quotes_root or data_dir / "raw/quotes"
    if not effective_funding_history_path.exists():
        raise FileNotFoundError(
            f"funding history artifact not found: {effective_funding_history_path}"
        )
    if max_oracle_lag_minutes <= 0:
        raise ValueError("max_oracle_lag_minutes must be > 0")

    history = pl.read_parquet(effective_funding_history_path)
    quote_logs = collect_quote_logs(effective_raw_quotes_root)
    if not quote_logs:
        raise FileNotFoundError(f"No raw quote JSONL files found under {effective_raw_quotes_root}")

    quotes_by_symbol: dict[str, list[dict[str, Any]]] = {}
    quote_skipped = {
        "missing_oracle_price": 0,
        "missing_raw_payload_ref": 0,
        "missing_raw_payload_sha256": 0,
    }
    for log in quote_logs:
        if log.oracle_price is None:
            quote_skipped["missing_oracle_price"] += 1
            continue
        if log.raw_payload_ref is None:
            quote_skipped["missing_raw_payload_ref"] += 1
            continue
        if not log.raw_payload_sha256:
            quote_skipped["missing_raw_payload_sha256"] += 1
            continue
        match_ts = _quote_match_ts_ms(log)
        if match_ts is None:
            continue
        match_ts_ms, match_ts_source = match_ts
        quotes_by_symbol.setdefault(log.canonical_symbol.upper(), []).append(
            {
                "match_ts_ms": match_ts_ms,
                "match_ts_source": match_ts_source,
                "recv_ts_ms": log.recv_ts_ms or match_ts_ms,
                "oracle_price": log.oracle_price,
                "raw_payload_ref": log.raw_payload_ref,
                "raw_payload_sha256": log.raw_payload_sha256,
            }
        )
    for rows in quotes_by_symbol.values():
        rows.sort(key=lambda item: int(item["match_ts_ms"]))

    max_lag_ms = int(max_oracle_lag_minutes * 60_000)
    rows: list[dict[str, Any]] = []
    skipped = {
        "missing_event_time": 0,
        "missing_symbol": 0,
        "missing_funding_rate": 0,
        "missing_raw_payload_ref": 0,
        "missing_raw_payload_sha256": 0,
        "missing_oracle_quote_for_symbol": 0,
        "missing_oracle_quote_within_lag": 0,
    }
    for source_row in history.to_dicts():
        event_ms = _to_int(source_row.get("source_time_ms")) or _ms_from_event_ts(
            source_row.get("funding_event_ts")
        )
        if event_ms is None:
            skipped["missing_event_time"] += 1
            continue
        canonical_symbol = str(source_row.get("canonical_symbol") or "").strip().upper()
        if not canonical_symbol:
            skipped["missing_symbol"] += 1
            continue
        funding_rate = _to_float(source_row.get("funding_rate"))
        if funding_rate is None:
            skipped["missing_funding_rate"] += 1
            continue
        history_raw_ref = str(source_row.get("raw_payload_ref") or "")
        if not history_raw_ref:
            skipped["missing_raw_payload_ref"] += 1
            continue
        history_hash = str(source_row.get("raw_payload_sha256") or "")
        if not history_hash:
            skipped["missing_raw_payload_sha256"] += 1
            continue
        quotes = quotes_by_symbol.get(canonical_symbol)
        if not quotes:
            skipped["missing_oracle_quote_for_symbol"] += 1
            continue
        quote = _nearest_oracle_quote(quotes, event_ms=event_ms, max_lag_ms=max_lag_ms)
        if quote is None:
            skipped["missing_oracle_quote_within_lag"] += 1
            continue
        lag_ms = abs(int(quote["match_ts_ms"]) - event_ms)
        oracle_raw_ref = str(quote["raw_payload_ref"])
        rows.append(
            {
                "schema_version": "funding_event.v1",
                "funding_event_ts": _iso_from_ms(event_ms),
                "canonical_symbol": canonical_symbol,
                "venue_symbol": source_row.get("venue_symbol"),
                "funding_rate": funding_rate,
                "funding_interval_minutes": FUNDING_INTERVAL_MINUTES,
                "oracle_price_at_funding": float(quote["oracle_price"]),
                "premium": _to_float(source_row.get("premium")),
                "impact_bid_px": None,
                "impact_ask_px": None,
                "impact_notional_usd": None,
                "source_ts_ms": event_ms,
                "recv_ts_ms": int(quote["recv_ts_ms"]),
                "raw_payload_sha256": history_hash,
                "raw_payload_ref": (
                    f"{history_raw_ref}|oracle_ref={oracle_raw_ref}|oracle_lag_ms={lag_ms}"
                ),
                "source": "hyperliquid_info.fundingHistory+trade_xyz_quote_oracle",
                "funding_history_raw_payload_ref": history_raw_ref,
                "oracle_raw_payload_ref": oracle_raw_ref,
                "oracle_join_lag_seconds": lag_ms / 1000,
                "oracle_join_ts_source": str(quote["match_ts_source"]),
                "notes": [
                    "oracle_price_at_funding joined from nearest quote oracle_price",
                    "source_ts_ms is the fundingHistory event time",
                    "recv_ts_ms is the matched quote receive time or quote match timestamp",
                ],
            }
        )

    raw_path = (
        data_dir
        / f"raw/funding/trade_xyz_from_history/{effective_generated_at.date().isoformat()}.jsonl"
    )
    parquet_path = data_dir / "normalized/funding_events_from_history.parquet"
    manifest_path = data_dir / "manifests/funding_history_join_manifest.json"
    _write_jsonl(rows, raw_path)
    _write_funding_events_parquet(rows, parquet_path)

    manifest = {
        "schema_version": "funding_history_join_manifest.v1",
        "generated_at": effective_generated_at.isoformat(),
        "funding_history_path": str(effective_funding_history_path),
        "raw_quotes_root": str(effective_raw_quotes_root),
        "raw_artifact_path": str(raw_path),
        "artifact_path": str(parquet_path),
        "source": "hyperliquid_info.fundingHistory+trade_xyz_quote_oracle",
        "row_count": len(rows),
        "history_row_count": history.height,
        "quote_log_count": len(quote_logs),
        "quote_oracle_symbol_count": len(quotes_by_symbol),
        "max_oracle_lag_minutes": max_oracle_lag_minutes,
        "skipped": skipped,
        "quote_skipped": quote_skipped,
        "usable_as_backtest_funding_event": bool(rows),
        "notes": [
            "Does not overwrite data/normalized/funding_events.parquet",
            "Use artifact_path with run_backtest funding_events when row_count > 0",
            "oracle_price_at_funding is joined from quote oracle_price with explicit lag provenance",
        ],
    }
    write_json(manifest_path, manifest)
    return manifest
