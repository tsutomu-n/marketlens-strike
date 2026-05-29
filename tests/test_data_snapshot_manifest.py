from __future__ import annotations

from datetime import datetime, timezone

from pydantic import ValidationError

from sis.research_protocol.data_snapshot import DataSnapshotManifest


def test_data_snapshot_manifest_records_data_lineage() -> None:
    manifest = DataSnapshotManifest(
        schema_version="data_snapshot_manifest.v1",
        data_snapshot_id="data-snap-001",
        generated_at=datetime.now(timezone.utc),
        quote_data_path="data/normalized/quotes.parquet",
        quote_data_sha256="abc",
        feature_panel_path="data/research/feature_panel.parquet",
        feature_panel_sha256="def",
        tracking_data_path="data/research/tracking_records.parquet",
        tracking_data_sha256="ghi",
        phase_gate_summary_path="data/ops/phase_gate_review_summary.json",
        phase_gate_decision="READ_ONLY_GO",
        symbols=["XYZ100", "SP500"],
        venues=["trade_xyz"],
        min_ts=datetime(2026, 1, 1, tzinfo=timezone.utc),
        max_ts=datetime(2026, 1, 2, tzinfo=timezone.utc),
        data_quality_summary={"issues": 0},
    )

    assert manifest.symbols == ["XYZ100", "SP500"]
    assert manifest.venues == ["trade_xyz"]


def test_data_snapshot_manifest_rejects_empty_symbols() -> None:
    try:
        DataSnapshotManifest(
            schema_version="data_snapshot_manifest.v1",
            data_snapshot_id="data-snap-001",
            generated_at=datetime.now(timezone.utc),
            quote_data_path="data/normalized/quotes.parquet",
            quote_data_sha256=None,
            feature_panel_path="data/research/feature_panel.parquet",
            feature_panel_sha256=None,
            tracking_data_path=None,
            tracking_data_sha256=None,
            phase_gate_summary_path=None,
            phase_gate_decision=None,
            symbols=[],
            venues=["trade_xyz"],
            min_ts=None,
            max_ts=None,
            data_quality_summary={},
        )
    except ValidationError as exc:
        assert "symbols" in str(exc)
    else:
        raise AssertionError("Expected empty symbols to fail")
