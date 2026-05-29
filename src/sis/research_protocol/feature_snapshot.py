from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, model_validator


class FeatureSnapshotManifest(BaseModel):
    schema_version: Literal["feature_snapshot_manifest.v1"]
    feature_snapshot_id: str
    generated_at: datetime
    input_data_snapshot_id: str
    feature_panel_path: str
    feature_panel_sha256: str | None
    feature_version: str
    feature_build_config_hash: str
    feature_cutoff_policy: str
    max_feature_source_ts: datetime | None
    leakage_checks: dict[str, Any]
    missing_rate_by_feature: dict[str, float]

    @model_validator(mode="after")
    def validate_manifest(self) -> FeatureSnapshotManifest:
        for field_name in (
            "feature_snapshot_id",
            "input_data_snapshot_id",
            "feature_panel_path",
            "feature_version",
            "feature_build_config_hash",
            "feature_cutoff_policy",
        ):
            if not str(getattr(self, field_name)).strip():
                raise ValueError(f"{field_name} must be non-empty")
        invalid = {
            feature: rate
            for feature, rate in self.missing_rate_by_feature.items()
            if rate < 0.0 or rate > 1.0
        }
        if invalid:
            raise ValueError(f"missing_rate_by_feature values must be between 0 and 1: {invalid}")
        return self
