from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from sis.research_protocol.feature_snapshot import FeatureSnapshotManifest


def test_feature_snapshot_manifest_records_feature_lineage() -> None:
    manifest = FeatureSnapshotManifest(
        schema_version="feature_snapshot_manifest.v1",
        feature_snapshot_id="feature-snap-001",
        generated_at=datetime.now(timezone.utc),
        input_data_snapshot_id="data-snap-001",
        feature_panel_path="data/research/feature_panel.parquet",
        feature_panel_sha256="abc",
        feature_version="v1",
        feature_build_config_hash="config-hash",
        feature_cutoff_policy="source_ts_lte_signal_ts",
        max_feature_source_ts=datetime(2026, 1, 1, tzinfo=timezone.utc),
        leakage_checks={"status": "pass"},
        missing_rate_by_feature={"vix_level": 0.0},
    )

    assert manifest.input_data_snapshot_id == "data-snap-001"
    assert manifest.missing_rate_by_feature["vix_level"] == 0.0


def test_feature_snapshot_manifest_rejects_invalid_missing_rate() -> None:
    with pytest.raises(ValidationError, match="missing_rate"):
        FeatureSnapshotManifest(
            schema_version="feature_snapshot_manifest.v1",
            feature_snapshot_id="feature-snap-001",
            generated_at=datetime.now(timezone.utc),
            input_data_snapshot_id="data-snap-001",
            feature_panel_path="data/research/feature_panel.parquet",
            feature_panel_sha256=None,
            feature_version="v1",
            feature_build_config_hash="config-hash",
            feature_cutoff_policy="source_ts_lte_signal_ts",
            max_feature_source_ts=None,
            leakage_checks={},
            missing_rate_by_feature={"vix_level": 1.2},
        )
