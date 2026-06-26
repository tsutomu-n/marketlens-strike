from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import datetime
from pathlib import Path
from typing import Any

SESSION_MISSING_FIELDS = (
    "external_session_ref",
    "internal_session_ref",
    "external_session_open",
    "internal_session_open",
    "maintenance_window",
    "holiday_closure",
)

SESSION_CALENDAR_NOTES = [
    "session refs are registry-derived",
    "open/holiday/maintenance flags remain null until observed or calendar-sourced",
]

ORACLE_TIMESTAMP_NOTES = [
    "oracle_ts_ms is accepted only when the asset context payload contains a known oracle timestamp field",
    "source_ts_ms from l2Book is not reused as oracle_ts_ms",
    "oracle_freshness_proxy is a separate snapshot timing proxy and must not be treated as oracle_ts_ms",
]


def session_missing_field_counts(session_rows: list[dict[str, Any]]) -> dict[str, int]:
    return {
        field: sum(
            1
            for row in session_rows
            if isinstance(row.get("missing_fields"), list) and field in row["missing_fields"]
        )
        for field in SESSION_MISSING_FIELDS
    }


def raw_quote_refs_hash_input(raw_payload_refs: Iterable[object]) -> str:
    return "\n".join(sorted(str(item) for item in raw_payload_refs if item))


def build_reference_datasets_manifest(
    *,
    generated_at: datetime,
    data_dir: Path,
    registry_path: Path,
    raw_quotes_root: Path,
    registry_parquet_path: Path,
    raw_fees_path: Path,
    fee_parquet_path: Path,
    raw_sessions_path: Path,
    session_parquet_path: Path,
    raw_funding_path: Path,
    funding_parquet_path: Path,
    oracle_timestamp_manifest_path: Path,
    registry_rows: list[dict[str, Any]],
    fee_rows: list[dict[str, Any]],
    session_rows: list[dict[str, Any]],
    funding_rows: list[dict[str, Any]],
    quote_logs_read: int,
    fee_source: Mapping[str, Any],
    oracle_timestamp: Mapping[str, Any],
    funding_skipped: Mapping[str, int],
    registry_source_hash: str,
    raw_quotes_root_source_hash: str,
) -> dict[str, Any]:
    return {
        "schema_version": "trade_xyz_reference_datasets_manifest.v1",
        "generated_at": generated_at.isoformat(),
        "data_dir": str(data_dir),
        "registry_path": str(registry_path),
        "raw_quotes_root": str(raw_quotes_root),
        "artifacts": {
            "instrument_registry_snapshots": str(registry_parquet_path),
            "raw_fee_snapshots": str(raw_fees_path),
            "fee_snapshots": str(fee_parquet_path),
            "raw_session_calendar_snapshots": str(raw_sessions_path),
            "session_calendar_snapshots": str(session_parquet_path),
            "raw_funding_events": str(raw_funding_path),
            "funding_events": str(funding_parquet_path),
            "oracle_timestamp_manifest": str(oracle_timestamp_manifest_path),
        },
        "row_counts": {
            "instrument_registry_snapshots": len(registry_rows),
            "fee_snapshots": len(fee_rows),
            "session_calendar_snapshots": len(session_rows),
            "funding_events": len(funding_rows),
            "quote_logs_read": quote_logs_read,
        },
        "fee_source": dict(fee_source),
        "oracle_timestamp": dict(oracle_timestamp),
        "session_missing_field_counts": session_missing_field_counts(session_rows),
        "funding_skipped": dict(funding_skipped),
        "source_hashes": {
            "registry": registry_source_hash,
            "raw_quotes_root": raw_quotes_root_source_hash,
        },
    }


def build_instrument_registry_manifest(
    *,
    generated_at: datetime,
    registry_path: Path,
    artifact_path: Path,
    row_count: int,
    source_hash: str,
) -> dict[str, Any]:
    return {
        "schema_version": "instrument_registry_manifest.v1",
        "generated_at": generated_at.isoformat(),
        "source_path": str(registry_path),
        "artifact_path": str(artifact_path),
        "row_count": row_count,
        "source_hash": source_hash,
    }


def build_fee_manifest(
    *,
    generated_at: datetime,
    registry_path: Path,
    raw_artifact_path: Path,
    artifact_path: Path,
    source_hash: str,
    fee_source: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": "fee_manifest.v1",
        "generated_at": generated_at.isoformat(),
        "source_path": str(registry_path),
        "raw_artifact_path": str(raw_artifact_path),
        "artifact_path": str(artifact_path),
        "source_hash": source_hash,
        **dict(fee_source),
    }


def build_session_calendar_manifest(
    *,
    generated_at: datetime,
    registry_path: Path,
    raw_artifact_path: Path,
    artifact_path: Path,
    row_count: int,
    missing_field_counts: Mapping[str, int],
) -> dict[str, Any]:
    return {
        "schema_version": "session_calendar_manifest.v1",
        "generated_at": generated_at.isoformat(),
        "source_path": str(registry_path),
        "raw_artifact_path": str(raw_artifact_path),
        "artifact_path": str(artifact_path),
        "row_count": row_count,
        "missing_field_counts": dict(missing_field_counts),
        "notes": SESSION_CALENDAR_NOTES,
    }


def build_funding_manifest(
    *,
    generated_at: datetime,
    raw_quotes_root: Path,
    raw_artifact_path: Path,
    artifact_path: Path,
    row_count: int,
    skipped: Mapping[str, int],
) -> dict[str, Any]:
    return {
        "schema_version": "funding_manifest.v1",
        "generated_at": generated_at.isoformat(),
        "source_path": str(raw_quotes_root),
        "raw_artifact_path": str(raw_artifact_path),
        "artifact_path": str(artifact_path),
        "row_count": row_count,
        "skipped": dict(skipped),
    }


def build_oracle_timestamp_manifest(
    *,
    generated_at: datetime,
    raw_quotes_root: Path,
    oracle_timestamp_summary: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": "oracle_timestamp_manifest.v1",
        "generated_at": generated_at.isoformat(),
        "source_path": str(raw_quotes_root),
        **dict(oracle_timestamp_summary),
        "notes": ORACLE_TIMESTAMP_NOTES,
    }
