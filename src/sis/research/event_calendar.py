from __future__ import annotations

from pathlib import Path

import polars as pl


def build_event_calendar(data_dir: Path, *, csv_path: Path | None = None) -> Path:
    source_path = csv_path or data_dir / "research/event_calendar.csv"
    if not source_path.exists():
        raise FileNotFoundError(f"Research event calendar CSV not found: {source_path}")

    frame = pl.read_csv(source_path, try_parse_dates=True)
    required = {
        "event_ts",
        "event_name",
        "event_class",
        "importance",
        "before_minutes",
        "after_minutes",
        "action",
    }
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"Event calendar CSV missing columns: {sorted(missing)}")

    normalized = frame.with_columns(
        pl.col("event_ts").cast(pl.Datetime(time_unit="us", time_zone="UTC")),
        pl.col("event_name").cast(pl.Utf8),
        pl.col("event_class").cast(pl.Utf8),
        pl.col("importance").cast(pl.Utf8).str.to_lowercase(),
        pl.col("before_minutes").cast(pl.Int64),
        pl.col("after_minutes").cast(pl.Int64),
        pl.col("action").cast(pl.Utf8).str.to_uppercase(),
    ).select(
        "event_ts",
        "event_name",
        "event_class",
        "importance",
        "before_minutes",
        "after_minutes",
        "action",
    )

    out = data_dir / "research/event_calendar.parquet"
    out.parent.mkdir(parents=True, exist_ok=True)
    normalized.sort("event_ts").write_parquet(out)
    return out
