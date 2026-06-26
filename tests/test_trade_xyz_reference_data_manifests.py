from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from sis.venues.trade_xyz.reference_data_manifests import (
    build_funding_manifest,
    build_oracle_timestamp_manifest,
    build_session_calendar_manifest,
    raw_quote_refs_hash_input,
    session_missing_field_counts,
)


def test_session_missing_field_counts_tracks_known_conservative_fields() -> None:
    rows = [
        {
            "missing_fields": [
                "external_session_ref",
                "maintenance_window",
                "holiday_closure",
            ]
        },
        {"missing_fields": ["maintenance_window", "unknown_future_field"]},
        {"missing_fields": "not-a-list"},
    ]

    assert session_missing_field_counts(rows) == {
        "external_session_ref": 1,
        "internal_session_ref": 0,
        "external_session_open": 0,
        "internal_session_open": 0,
        "maintenance_window": 2,
        "holiday_closure": 1,
    }


def test_raw_quote_refs_hash_input_sorts_and_skips_missing_refs() -> None:
    assert raw_quote_refs_hash_input(["b.jsonl#row=1", None, "a.jsonl#row=0", ""]) == (
        "a.jsonl#row=0\nb.jsonl#row=1"
    )


def test_session_calendar_manifest_preserves_notes_and_missing_counts() -> None:
    payload = build_session_calendar_manifest(
        generated_at=datetime(2026, 5, 26, 1, tzinfo=timezone.utc),
        registry_path=Path("data/registry.json"),
        raw_artifact_path=Path("data/raw/sessions/trade_xyz/2026-05-26.jsonl"),
        artifact_path=Path("data/normalized/session_calendar_snapshots.parquet"),
        row_count=2,
        missing_field_counts={"maintenance_window": 2},
    )

    assert payload == {
        "schema_version": "session_calendar_manifest.v1",
        "generated_at": "2026-05-26T01:00:00+00:00",
        "source_path": "data/registry.json",
        "raw_artifact_path": "data/raw/sessions/trade_xyz/2026-05-26.jsonl",
        "artifact_path": "data/normalized/session_calendar_snapshots.parquet",
        "row_count": 2,
        "missing_field_counts": {"maintenance_window": 2},
        "notes": [
            "session refs are registry-derived",
            "open/holiday/maintenance flags remain null until observed or calendar-sourced",
        ],
    }


def test_oracle_timestamp_manifest_preserves_boundary_notes() -> None:
    payload = build_oracle_timestamp_manifest(
        generated_at=datetime(2026, 5, 26, 1, tzinfo=timezone.utc),
        raw_quotes_root=Path("data/raw/quotes"),
        oracle_timestamp_summary={
            "oracle_ts_present_count": 0,
            "oracle_ts_missing_count": 1,
        },
    )

    assert payload["schema_version"] == "oracle_timestamp_manifest.v1"
    assert payload["generated_at"] == "2026-05-26T01:00:00+00:00"
    assert payload["source_path"] == "data/raw/quotes"
    assert payload["oracle_ts_missing_count"] == 1
    assert "source_ts_ms from l2Book is not reused as oracle_ts_ms" in payload["notes"]
    assert (
        "oracle_freshness_proxy is a separate snapshot timing proxy and must not be treated as oracle_ts_ms"
        in payload["notes"]
    )


def test_funding_manifest_preserves_skipped_payload() -> None:
    payload = build_funding_manifest(
        generated_at=datetime(2026, 5, 26, 1, tzinfo=timezone.utc),
        raw_quotes_root=Path("data/raw/quotes"),
        raw_artifact_path=Path("data/raw/funding/trade_xyz/2026-05-26.jsonl"),
        artifact_path=Path("data/normalized/funding_events.parquet"),
        row_count=3,
        skipped={"missing_funding": 2},
    )

    assert payload == {
        "schema_version": "funding_manifest.v1",
        "generated_at": "2026-05-26T01:00:00+00:00",
        "source_path": "data/raw/quotes",
        "raw_artifact_path": "data/raw/funding/trade_xyz/2026-05-26.jsonl",
        "artifact_path": "data/normalized/funding_events.parquet",
        "row_count": 3,
        "skipped": {"missing_funding": 2},
    }
