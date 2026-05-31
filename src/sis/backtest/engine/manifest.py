from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Literal

import polars as pl
from pydantic import BaseModel, Field

from sis.backtest.engine.config import BacktestConfig
from sis.backtest.engine.data_quality import DataQualityReport, apply_period_filter
from sis.backtest.engine.hashing import config_hash, frame_sha256, input_schema_hash


class DataManifest(BaseModel):
    schema_version: Literal["trade_xyz_backtest_data_manifest.v1"] = (
        "trade_xyz_backtest_data_manifest.v1"
    )
    run_id: str
    input_data_ref: str
    input_data_sha256: str
    input_file_sha256: str | None = None
    input_schema_hash: str
    config_hash: str
    input_row_count: int
    filtered_row_count: int
    first_event_ts: datetime | None = None
    last_event_ts: datetime | None = None
    symbols: list[str] = Field(default_factory=list)
    timeframe: str
    event_time_source: str
    close_source: str = "close"
    bar_builder: str | None = None
    data_is_runtime_artifact: bool = True
    warmup_start_ts: datetime | None = None
    evaluation_start_ts: datetime
    evaluation_end_ts: datetime
    data_quality_summary: dict[str, Any] = Field(default_factory=dict)
    data_readiness_summary: dict[str, Any] = Field(default_factory=dict)


def build_data_manifest(
    *,
    config: BacktestConfig,
    frame: pl.DataFrame,
    input_data_ref: str,
    data_quality: DataQualityReport,
    event_time_source: str,
    close_source: str = "close",
    bar_builder: str | None = None,
) -> DataManifest:
    filtered = apply_period_filter(frame, config=config)
    symbols = (
        sorted(str(value) for value in filtered.get_column("symbol").drop_nulls().unique())
        if "symbol" in filtered.columns
        else []
    )
    raw_first_ts = filtered.get_column("event_ts").min() if not filtered.is_empty() else None
    raw_last_ts = filtered.get_column("event_ts").max() if not filtered.is_empty() else None
    first_ts = raw_first_ts if isinstance(raw_first_ts, datetime) else None
    last_ts = raw_last_ts if isinstance(raw_last_ts, datetime) else None
    input_path = Path(input_data_ref)
    input_file_sha256 = _file_sha256(input_path) if input_path.exists() else None
    quality_payload = data_quality.model_dump(mode="json")
    return DataManifest(
        run_id=config.run_id,
        input_data_ref=input_data_ref,
        input_data_sha256=frame_sha256(frame),
        input_file_sha256=input_file_sha256,
        input_schema_hash=input_schema_hash(frame),
        config_hash=config_hash(config),
        input_row_count=frame.height,
        filtered_row_count=filtered.height,
        first_event_ts=first_ts,
        last_event_ts=last_ts,
        symbols=symbols,
        timeframe=config.timeframe,
        event_time_source=event_time_source,
        close_source=close_source,
        bar_builder=bar_builder,
        warmup_start_ts=config.period.warmup_start_ts,
        evaluation_start_ts=config.period.evaluation_start_ts,
        evaluation_end_ts=config.period.evaluation_end_ts,
        data_quality_summary=quality_payload,
        data_readiness_summary={
            "fee_unresolved_rate": quality_payload.get("fee_unresolved_rate"),
            "funding_interval_missing_rate": quality_payload.get("funding_interval_missing_rate"),
            "oracle_ts_missing_rate": quality_payload.get("oracle_ts_missing_rate"),
            "raw_payload_ref_missing_rate": quality_payload.get("raw_payload_ref_missing_rate"),
            "oi_cap_usage_missing_rate": quality_payload.get("oi_cap_usage_missing_rate"),
            "discovery_bound_missing_rate": quality_payload.get("discovery_bound_missing_rate"),
            "bound_distance_missing_rate": quality_payload.get("bound_distance_missing_rate"),
        },
    )


def _file_sha256(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
