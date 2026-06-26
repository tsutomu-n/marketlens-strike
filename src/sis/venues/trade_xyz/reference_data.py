from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any

import polars as pl

from sis.storage.jsonl_store import write_json
from sis.storage.normalize import collect_quote_logs
from sis.venues.trade_xyz.registry import load_trade_xyz_registry
from sis.venues.trade_xyz.reference_data_funding import funding_event_rows as _funding_event_rows
from sis.venues.trade_xyz.reference_data_manifests import (
    build_fee_manifest as _build_fee_manifest,
)
from sis.venues.trade_xyz.reference_data_manifests import (
    build_funding_manifest as _build_funding_manifest,
)
from sis.venues.trade_xyz.reference_data_manifests import (
    build_instrument_registry_manifest as _build_instrument_registry_manifest,
)
from sis.venues.trade_xyz.reference_data_manifests import (
    build_oracle_timestamp_manifest as _build_oracle_timestamp_manifest,
)
from sis.venues.trade_xyz.reference_data_manifests import (
    build_reference_datasets_manifest as _build_reference_datasets_manifest,
)
from sis.venues.trade_xyz.reference_data_manifests import (
    build_session_calendar_manifest as _build_session_calendar_manifest,
)
from sis.venues.trade_xyz.reference_data_manifests import (
    raw_quote_refs_hash_input as _raw_quote_refs_hash_input,
)
from sis.venues.trade_xyz.reference_data_oracle import (
    build_oracle_timestamp_summary as _oracle_timestamp_summary,
)
from sis.venues.trade_xyz.reference_data_rows import fee_snapshot_rows as _fee_snapshot_rows
from sis.venues.trade_xyz.reference_data_rows import fee_source_summary as _fee_source_summary
from sis.venues.trade_xyz.reference_data_rows import (
    registry_snapshot_rows as _registry_snapshot_rows,
)
from sis.venues.trade_xyz.reference_data_rows import (
    session_calendar_snapshot_rows as _session_calendar_snapshot_rows,
)


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

    oracle_timestamp_manifest_path = manifest_dir / "oracle_timestamp_manifest.json"
    manifest = _build_reference_datasets_manifest(
        generated_at=effective_snapshot_ts,
        data_dir=data_dir,
        registry_path=effective_registry_path,
        raw_quotes_root=effective_raw_quotes_root,
        registry_parquet_path=registry_parquet_path,
        raw_fees_path=raw_fees_path,
        fee_parquet_path=fee_parquet_path,
        raw_sessions_path=raw_sessions_path,
        session_parquet_path=session_parquet_path,
        raw_funding_path=raw_funding_path,
        funding_parquet_path=funding_parquet_path,
        oracle_timestamp_manifest_path=oracle_timestamp_manifest_path,
        registry_rows=registry_rows,
        fee_rows=fee_rows,
        session_rows=session_rows,
        funding_rows=funding_rows,
        quote_logs_read=len(logs),
        fee_source=fee_source_summary,
        oracle_timestamp=oracle_timestamp_summary,
        funding_skipped=funding_skipped,
        registry_source_hash=registry_source_hash,
        raw_quotes_root_source_hash=_sha256_text(
            _raw_quote_refs_hash_input(item.raw_payload_ref for item in logs)
        ),
    )
    write_json(manifest_dir / "trade_xyz_reference_datasets_manifest.json", manifest)
    write_json(
        manifest_dir / "instrument_registry_manifest.json",
        _build_instrument_registry_manifest(
            generated_at=effective_snapshot_ts,
            registry_path=effective_registry_path,
            artifact_path=registry_parquet_path,
            row_count=len(registry_rows),
            source_hash=registry_source_hash,
        ),
    )
    write_json(
        manifest_dir / "fee_manifest.json",
        _build_fee_manifest(
            generated_at=effective_snapshot_ts,
            registry_path=effective_registry_path,
            raw_artifact_path=raw_fees_path,
            artifact_path=fee_parquet_path,
            source_hash=registry_source_hash,
            fee_source=fee_source_summary,
        ),
    )
    write_json(
        manifest_dir / "session_calendar_manifest.json",
        _build_session_calendar_manifest(
            generated_at=effective_snapshot_ts,
            registry_path=effective_registry_path,
            raw_artifact_path=raw_sessions_path,
            artifact_path=session_parquet_path,
            row_count=len(session_rows),
            missing_field_counts=manifest["session_missing_field_counts"],
        ),
    )
    write_json(
        manifest_dir / "funding_manifest.json",
        _build_funding_manifest(
            generated_at=effective_snapshot_ts,
            raw_quotes_root=effective_raw_quotes_root,
            raw_artifact_path=raw_funding_path,
            artifact_path=funding_parquet_path,
            row_count=len(funding_rows),
            skipped=funding_skipped,
        ),
    )
    write_json(
        oracle_timestamp_manifest_path,
        _build_oracle_timestamp_manifest(
            generated_at=effective_snapshot_ts,
            raw_quotes_root=effective_raw_quotes_root,
            oracle_timestamp_summary=oracle_timestamp_summary,
        ),
    )
    return manifest
