from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, model_validator


class DataSnapshotManifest(BaseModel):
    schema_version: Literal["data_snapshot_manifest.v1"]
    data_snapshot_id: str
    generated_at: datetime
    quote_data_path: str
    quote_data_sha256: str | None
    feature_panel_path: str
    feature_panel_sha256: str | None
    tracking_data_path: str | None
    tracking_data_sha256: str | None
    phase_gate_summary_path: str | None
    phase_gate_decision: str | None
    symbols: list[str]
    venues: list[str]
    min_ts: datetime | None
    max_ts: datetime | None
    data_quality_summary: dict[str, Any]

    @model_validator(mode="after")
    def validate_manifest(self) -> DataSnapshotManifest:
        if not self.data_snapshot_id.strip():
            raise ValueError("data_snapshot_id must be non-empty")
        if not self.quote_data_path.strip():
            raise ValueError("quote_data_path must be non-empty")
        if not self.feature_panel_path.strip():
            raise ValueError("feature_panel_path must be non-empty")
        if not self.symbols:
            raise ValueError("symbols must contain at least one symbol")
        if not self.venues:
            raise ValueError("venues must contain at least one venue")
        if self.min_ts is not None and self.max_ts is not None and self.min_ts > self.max_ts:
            raise ValueError("min_ts must be <= max_ts")
        self.symbols = [symbol.strip().upper() for symbol in self.symbols if symbol.strip()]
        self.venues = [venue.strip() for venue in self.venues if venue.strip()]
        if not self.symbols:
            raise ValueError("symbols must contain at least one non-empty symbol")
        if not self.venues:
            raise ValueError("venues must contain at least one non-empty venue")
        return self
