from __future__ import annotations

from collections import OrderedDict
from datetime import datetime, timezone
from typing import Any

from sis.models import QuoteLog


def event_ts_ms(log: QuoteLog) -> tuple[int | None, str | None]:
    if log.source_ts_ms is not None:
        return log.source_ts_ms, None
    if log.recv_ts_ms is not None:
        return log.recv_ts_ms, "source_ts_ms_fallback=recv_ts_ms"
    return int(log.ts_client.timestamp() * 1000), "source_ts_ms_fallback=ts_client"


def hour_bucket(ms: int) -> int:
    return (ms // 3_600_000) * 3_600_000


def iso_from_ms(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).isoformat()


def funding_event_rows(logs: list[QuoteLog]) -> tuple[list[dict[str, Any]], dict[str, int]]:
    latest_by_symbol_hour: OrderedDict[tuple[str, int], dict[str, Any]] = OrderedDict()
    skipped = {
        "missing_funding_rate": 0,
        "missing_funding_interval_minutes": 0,
        "missing_oracle_price": 0,
        "missing_recv_ts_ms": 0,
        "missing_raw_payload_ref": 0,
    }
    for log in sorted(logs, key=lambda item: (item.canonical_symbol, item.ts_client)):
        if log.funding_rate is None:
            skipped["missing_funding_rate"] += 1
            continue
        if log.funding_interval_minutes is None:
            skipped["missing_funding_interval_minutes"] += 1
            continue
        if log.oracle_price is None:
            skipped["missing_oracle_price"] += 1
            continue
        if log.recv_ts_ms is None:
            skipped["missing_recv_ts_ms"] += 1
            continue
        if log.raw_payload_ref is None:
            skipped["missing_raw_payload_ref"] += 1
            continue

        event_ms, fallback_note = event_ts_ms(log)
        if event_ms is None:
            continue
        bucket = hour_bucket(event_ms)
        row: dict[str, Any] = {
            "schema_version": "funding_event.v1",
            "funding_event_ts": iso_from_ms(bucket),
            "canonical_symbol": log.canonical_symbol,
            "venue_symbol": log.venue_symbol,
            "funding_rate": log.funding_rate,
            "funding_interval_minutes": log.funding_interval_minutes,
            "oracle_price_at_funding": log.oracle_price,
            "premium": log.premium,
            "impact_bid_px": None,
            "impact_ask_px": None,
            "impact_notional_usd": None,
            "source_ts_ms": event_ms,
            "recv_ts_ms": log.recv_ts_ms,
            "raw_payload_sha256": log.raw_payload_sha256,
            "raw_payload_ref": log.raw_payload_ref,
        }
        if fallback_note is not None:
            row["notes"] = [fallback_note]
        latest_by_symbol_hour[(log.canonical_symbol, bucket)] = row
    return list(latest_by_symbol_hour.values()), skipped
