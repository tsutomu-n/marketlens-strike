from __future__ import annotations

from collections import OrderedDict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any

import polars as pl

from sis.models import InstrumentSpec, QuoteLog
from sis.storage.jsonl_store import write_json
from sis.storage.normalize import collect_quote_logs
from sis.venues.trade_xyz.registry import load_trade_xyz_registry


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _file_sha256(path: Path) -> str | None:
    if not path.exists():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _event_ts_ms(log: QuoteLog) -> tuple[int | None, str | None]:
    if log.source_ts_ms is not None:
        return log.source_ts_ms, None
    if log.recv_ts_ms is not None:
        return log.recv_ts_ms, "source_ts_ms_fallback=recv_ts_ms"
    return int(log.ts_client.timestamp() * 1000), "source_ts_ms_fallback=ts_client"


def _hour_bucket(ms: int) -> int:
    return (ms // 3_600_000) * 3_600_000


def _iso_from_ms(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).isoformat()


def _write_parquet(rows: list[dict[str, Any]], path: Path) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame = pl.from_dicts(rows, infer_schema_length=None) if rows else pl.DataFrame()
    frame.write_parquet(path)
    return frame.height


def _write_jsonl(rows: list[dict[str, Any]], path: Path) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
    return len(rows)


def _registry_snapshot_rows(
    instruments: list[InstrumentSpec],
    *,
    snapshot_ts: datetime,
    source_url: str,
    source_hash: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in instruments:
        discovery_bound_pct = (
            item.discovery_bound_bps / 10_000 if item.discovery_bound_bps is not None else None
        )
        rows.append(
            {
                "schema_version": "instrument_registry_snapshot.v1",
                "snapshot_ts": snapshot_ts.isoformat(),
                "canonical_symbol": item.canonical_symbol,
                "venue_symbol": item.venue_symbol,
                "dex": item.dex or "xyz",
                "coin": item.coin or f"xyz:{item.canonical_symbol}",
                "asset_id": item.asset_id,
                "underlying": item.real_market_symbol,
                "asset_class": item.asset_class.value,
                "max_leverage": item.max_leverage,
                "margin_mode": None,
                "discovery_bound_pct": discovery_bound_pct,
                "discovery_bound_bps": item.discovery_bound_bps,
                "open_interest_cap_usd": item.oi_cap_usd,
                "external_session_hours": item.external_session,
                "internal_session_hours": item.internal_session,
                "holiday_calendar_ref": None,
                "fee_mode": item.fee_mode,
                "tick_size": None,
                "lot_size": None,
                "min_order_size": None,
                "min_notional_usd": None,
                "source_url": source_url,
                "source_hash": source_hash,
            }
        )
    return rows


def _fee_snapshot_rows(
    instruments: list[InstrumentSpec],
    *,
    snapshot_ts: datetime,
    source: str,
    source_hash: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in instruments:
        if item.fee_mode is None or item.taker_fee_bps is None or item.maker_fee_bps is None:
            continue
        rows.append(
            {
                "schema_version": "fee_snapshot.v1",
                "snapshot_ts": snapshot_ts.isoformat(),
                "canonical_symbol": item.canonical_symbol,
                "venue_symbol": item.venue_symbol,
                "fee_mode": item.fee_mode,
                "fee_tier": None,
                "taker_fee_bps": item.taker_fee_bps,
                "maker_fee_bps": item.maker_fee_bps,
                "builder_fee_bps": None,
                "staking_discount_bps": None,
                "source": source,
                "source_hash": source_hash,
            }
        )
    return rows


def _fee_source_summary(
    instruments: list[InstrumentSpec],
    fee_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    resolved_symbols = {str(row["canonical_symbol"]) for row in fee_rows}
    unresolved_symbols = [
        item.canonical_symbol
        for item in instruments
        if item.canonical_symbol not in resolved_symbols
    ]
    source_counts: dict[str, int] = {}
    mode_counts: dict[str, int] = {}
    for row in fee_rows:
        source = str(row.get("source") or "unknown")
        mode = str(row.get("fee_mode") or "unknown")
        source_counts[source] = source_counts.get(source, 0) + 1
        mode_counts[mode] = mode_counts.get(mode, 0) + 1
    account_specific_missing_fields = [
        "fee_tier",
        "builder_fee_bps",
        "staking_discount_bps",
        "account_growth_mode",
    ]
    return {
        "instrument_count": len(instruments),
        "fee_snapshot_count": len(fee_rows),
        "resolved_symbol_count": len(resolved_symbols),
        "unresolved_symbol_count": len(unresolved_symbols),
        "unresolved_symbols": unresolved_symbols,
        "fee_mode_counts": mode_counts,
        "fee_source_counts": source_counts,
        "account_specific_fee_status": "not_collected_no_wallet_or_user_context",
        "account_specific_missing_fields": account_specific_missing_fields,
        "account_specific_missing_field_counts": {
            field: len(fee_rows) for field in account_specific_missing_fields
        },
        "notes": [
            "fee_snapshots are registry/config-derived unless source points to an observed fee feed",
            "wallet/signing/exchange-write remain out of scope for this pure backtest data path",
        ],
    }


def _session_calendar_snapshot_rows(
    instruments: list[InstrumentSpec],
    *,
    snapshot_ts: datetime,
    source: str,
    source_hash: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in instruments:
        missing_fields: list[str] = []
        if item.external_session is None:
            missing_fields.append("external_session_ref")
        if item.internal_session is None:
            missing_fields.append("internal_session_ref")
        missing_fields.extend(
            [
                "external_session_open",
                "internal_session_open",
                "maintenance_window",
                "holiday_closure",
            ]
        )
        notes = [
            "registry_derived_session_refs_only",
            "do_not_treat_null_open_flags_as_observed_session_state",
        ]
        rows.append(
            {
                "schema_version": "session_calendar_snapshot.v1",
                "snapshot_ts": snapshot_ts.isoformat(),
                "canonical_symbol": item.canonical_symbol,
                "venue_symbol": item.venue_symbol,
                "real_market_symbol": item.real_market_symbol,
                "asset_class": item.asset_class.value,
                "timezone": None,
                "external_session_ref": item.external_session,
                "internal_session_ref": item.internal_session,
                "external_session_open": None,
                "internal_session_open": None,
                "maintenance_window": None,
                "holiday_closure": None,
                "close_only_allowed": True,
                "source": source,
                "source_hash": source_hash,
                "data_status": "incomplete" if missing_fields else "registry_derived",
                "missing_fields": missing_fields,
                "notes": notes,
            }
        )
    return rows


def _funding_event_rows(logs: list[QuoteLog]) -> tuple[list[dict[str, Any]], dict[str, int]]:
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

        event_ms, fallback_note = _event_ts_ms(log)
        if event_ms is None:
            continue
        bucket = _hour_bucket(event_ms)
        row = {
            "schema_version": "funding_event.v1",
            "funding_event_ts": _iso_from_ms(bucket),
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


def _oracle_timestamp_summary(logs: list[QuoteLog]) -> dict[str, Any]:
    status_counts: dict[str, int] = {}
    missing_reasons: dict[str, int] = {}
    source_counts: dict[str, int] = {}
    per_symbol: dict[str, dict[str, Any]] = {}
    for log in logs:
        status = log.oracle_ts_status or ("observed" if log.oracle_ts_ms is not None else "unknown")
        reason = log.oracle_ts_missing_reason or (
            "none" if log.oracle_ts_ms is not None else "missing_reason_not_recorded"
        )
        source = log.oracle_ts_source or "none"
        status_counts[status] = status_counts.get(status, 0) + 1
        source_counts[source] = source_counts.get(source, 0) + 1
        if log.oracle_ts_ms is None:
            missing_reasons[reason] = missing_reasons.get(reason, 0) + 1

        symbol_entry = per_symbol.setdefault(
            log.canonical_symbol,
            {
                "row_count": 0,
                "oracle_ts_present_count": 0,
                "oracle_ts_missing_count": 0,
                "oracle_ts_status_counts": {},
                "oracle_ts_missing_reasons": {},
            },
        )
        symbol_entry["row_count"] += 1
        if log.oracle_ts_ms is None:
            symbol_entry["oracle_ts_missing_count"] += 1
            symbol_entry["oracle_ts_missing_reasons"][reason] = (
                symbol_entry["oracle_ts_missing_reasons"].get(reason, 0) + 1
            )
        else:
            symbol_entry["oracle_ts_present_count"] += 1
        symbol_entry["oracle_ts_status_counts"][status] = (
            symbol_entry["oracle_ts_status_counts"].get(status, 0) + 1
        )

    return {
        "row_count": len(logs),
        "oracle_ts_present_count": sum(1 for log in logs if log.oracle_ts_ms is not None),
        "oracle_ts_missing_count": sum(1 for log in logs if log.oracle_ts_ms is None),
        "oracle_ts_present_rate": (
            sum(1 for log in logs if log.oracle_ts_ms is not None) / len(logs) if logs else 0.0
        ),
        "oracle_ts_status_counts": status_counts,
        "oracle_ts_source_counts": source_counts,
        "oracle_ts_missing_reasons": missing_reasons,
        "per_symbol": per_symbol,
        "searched_payload_fields": [
            "oracleTs",
            "oracle_ts",
            "oracleTsMs",
            "oracle_ts_ms",
            "oracleTime",
            "oracle_time",
            "oracleTimestamp",
            "oracle_timestamp",
        ],
    }


def build_trade_xyz_reference_datasets(
    *,
    data_dir: Path,
    registry_path: Path | None = None,
    raw_quotes_root: Path | None = None,
    snapshot_ts: datetime | None = None,
) -> dict[str, Any]:
    effective_snapshot_ts = snapshot_ts or _utc_now()
    effective_registry_path = (
        registry_path or data_dir / "registry/trade_xyz_instrument_registry.json"
    )
    effective_raw_quotes_root = raw_quotes_root or data_dir / "raw/quotes"
    instruments = load_trade_xyz_registry(effective_registry_path)
    logs = collect_quote_logs(effective_raw_quotes_root)
    if not logs:
        raise FileNotFoundError(f"No raw quote JSONL files found under {effective_raw_quotes_root}")

    registry_source_hash = _file_sha256(effective_registry_path) or _sha256_text(
        effective_registry_path.as_posix()
    )
    registry_rows = _registry_snapshot_rows(
        instruments,
        snapshot_ts=effective_snapshot_ts,
        source_url=str(effective_registry_path),
        source_hash=registry_source_hash,
    )
    fee_rows = _fee_snapshot_rows(
        instruments,
        snapshot_ts=effective_snapshot_ts,
        source=str(effective_registry_path),
        source_hash=registry_source_hash,
    )
    session_rows = _session_calendar_snapshot_rows(
        instruments,
        snapshot_ts=effective_snapshot_ts,
        source=str(effective_registry_path),
        source_hash=registry_source_hash,
    )
    funding_rows, funding_skipped = _funding_event_rows(logs)
    oracle_timestamp_summary = _oracle_timestamp_summary(logs)
    fee_source_summary = _fee_source_summary(instruments, fee_rows)

    normalized_dir = data_dir / "normalized"
    raw_fees_path = data_dir / f"raw/fees/trade_xyz/{effective_snapshot_ts.date()}.jsonl"
    raw_funding_path = data_dir / f"raw/funding/trade_xyz/{effective_snapshot_ts.date()}.jsonl"
    raw_sessions_path = data_dir / f"raw/sessions/trade_xyz/{effective_snapshot_ts.date()}.jsonl"
    registry_parquet_path = normalized_dir / "instrument_registry_snapshots.parquet"
    fee_parquet_path = normalized_dir / "fee_snapshots.parquet"
    session_parquet_path = normalized_dir / "session_calendar_snapshots.parquet"
    funding_parquet_path = normalized_dir / "funding_events.parquet"
    manifest_dir = data_dir / "manifests"

    _write_parquet(registry_rows, registry_parquet_path)
    _write_jsonl(fee_rows, raw_fees_path)
    _write_parquet(fee_rows, fee_parquet_path)
    _write_jsonl(session_rows, raw_sessions_path)
    _write_parquet(session_rows, session_parquet_path)
    _write_jsonl(funding_rows, raw_funding_path)
    _write_parquet(funding_rows, funding_parquet_path)

    manifest = {
        "schema_version": "trade_xyz_reference_datasets_manifest.v1",
        "generated_at": effective_snapshot_ts.isoformat(),
        "data_dir": str(data_dir),
        "registry_path": str(effective_registry_path),
        "raw_quotes_root": str(effective_raw_quotes_root),
        "artifacts": {
            "instrument_registry_snapshots": str(registry_parquet_path),
            "raw_fee_snapshots": str(raw_fees_path),
            "fee_snapshots": str(fee_parquet_path),
            "raw_session_calendar_snapshots": str(raw_sessions_path),
            "session_calendar_snapshots": str(session_parquet_path),
            "raw_funding_events": str(raw_funding_path),
            "funding_events": str(funding_parquet_path),
            "oracle_timestamp_manifest": str(manifest_dir / "oracle_timestamp_manifest.json"),
        },
        "row_counts": {
            "instrument_registry_snapshots": len(registry_rows),
            "fee_snapshots": len(fee_rows),
            "session_calendar_snapshots": len(session_rows),
            "funding_events": len(funding_rows),
            "quote_logs_read": len(logs),
        },
        "fee_source": fee_source_summary,
        "oracle_timestamp": oracle_timestamp_summary,
        "session_missing_field_counts": {
            field: sum(1 for row in session_rows if field in row["missing_fields"])
            for field in (
                "external_session_ref",
                "internal_session_ref",
                "external_session_open",
                "internal_session_open",
                "maintenance_window",
                "holiday_closure",
            )
        },
        "funding_skipped": funding_skipped,
        "source_hashes": {
            "registry": registry_source_hash,
            "raw_quotes_root": _sha256_text(
                "\n".join(
                    sorted(str(item.raw_payload_ref) for item in logs if item.raw_payload_ref)
                )
            ),
        },
    }
    write_json(manifest_dir / "trade_xyz_reference_datasets_manifest.json", manifest)
    write_json(
        manifest_dir / "instrument_registry_manifest.json",
        {
            "schema_version": "instrument_registry_manifest.v1",
            "generated_at": effective_snapshot_ts.isoformat(),
            "source_path": str(effective_registry_path),
            "artifact_path": str(registry_parquet_path),
            "row_count": len(registry_rows),
            "source_hash": registry_source_hash,
        },
    )
    write_json(
        manifest_dir / "fee_manifest.json",
        {
            "schema_version": "fee_manifest.v1",
            "generated_at": effective_snapshot_ts.isoformat(),
            "source_path": str(effective_registry_path),
            "raw_artifact_path": str(raw_fees_path),
            "artifact_path": str(fee_parquet_path),
            "source_hash": registry_source_hash,
            **fee_source_summary,
        },
    )
    write_json(
        manifest_dir / "session_calendar_manifest.json",
        {
            "schema_version": "session_calendar_manifest.v1",
            "generated_at": effective_snapshot_ts.isoformat(),
            "source_path": str(effective_registry_path),
            "raw_artifact_path": str(raw_sessions_path),
            "artifact_path": str(session_parquet_path),
            "row_count": len(session_rows),
            "missing_field_counts": manifest["session_missing_field_counts"],
            "notes": [
                "session refs are registry-derived",
                "open/holiday/maintenance flags remain null until observed or calendar-sourced",
            ],
        },
    )
    write_json(
        manifest_dir / "funding_manifest.json",
        {
            "schema_version": "funding_manifest.v1",
            "generated_at": effective_snapshot_ts.isoformat(),
            "source_path": str(effective_raw_quotes_root),
            "raw_artifact_path": str(raw_funding_path),
            "artifact_path": str(funding_parquet_path),
            "row_count": len(funding_rows),
            "skipped": funding_skipped,
        },
    )
    write_json(
        manifest_dir / "oracle_timestamp_manifest.json",
        {
            "schema_version": "oracle_timestamp_manifest.v1",
            "generated_at": effective_snapshot_ts.isoformat(),
            "source_path": str(effective_raw_quotes_root),
            **oracle_timestamp_summary,
            "notes": [
                "oracle_ts_ms is accepted only when the asset context payload contains a known oracle timestamp field",
                "source_ts_ms from l2Book is not reused as oracle_ts_ms",
            ],
        },
    )
    return manifest
