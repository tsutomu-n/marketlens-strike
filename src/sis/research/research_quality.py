from __future__ import annotations

from pathlib import Path

import polars as pl

from sis.storage.jsonl_store import write_json


def _dataset_summary(frame: pl.DataFrame, time_column: str | None) -> dict:
    summary = {
        "rows": frame.height,
        "columns": frame.columns,
        "missing_by_column": {name: int(frame.get_column(name).null_count()) for name in frame.columns},
        "duplicate_rows": int(frame.is_duplicated().sum()) if frame.height else 0,
    }
    if time_column and time_column in frame.columns and frame.height:
        series = frame.get_column(time_column)
        summary["min_time"] = str(series.min())
        summary["max_time"] = str(series.max())
    return summary


def build_research_quality_report(data_dir: Path) -> Path:
    paths = {
        "market_panel": data_dir / "research/market_panel.parquet",
        "macro_panel": data_dir / "research/macro_panel.parquet",
        "event_calendar": data_dir / "research/event_calendar.parquet",
        "feature_panel": data_dir / "research/feature_panel.parquet",
        "signals": data_dir / "research/signals.csv",
    }
    summaries: dict[str, dict] = {}

    market = pl.read_parquet(paths["market_panel"])
    summaries["market_panel"] = _dataset_summary(market, "ts")
    summaries["market_panel"]["symbol_coverage"] = sorted(set(market.get_column("symbol").to_list()))

    macro = pl.read_parquet(paths["macro_panel"])
    summaries["macro_panel"] = _dataset_summary(macro, "date")
    summaries["macro_panel"]["series_coverage"] = sorted(set(macro.get_column("series_id").to_list()))

    event_calendar = pl.read_parquet(paths["event_calendar"]) if paths["event_calendar"].exists() else pl.DataFrame()
    summaries["event_calendar"] = _dataset_summary(event_calendar, "event_ts" if "event_ts" in event_calendar.columns else None)

    feature = pl.read_parquet(paths["feature_panel"])
    summaries["feature_panel"] = _dataset_summary(feature, "ts")
    summaries["feature_panel"]["trade_allowed_rate"] = (
        float(feature.get_column("trade_allowed").mean()) if feature.height and "trade_allowed" in feature.columns else None
    )

    signals = pl.read_csv(paths["signals"])
    summaries["signals"] = _dataset_summary(signals, "ts_signal" if "ts_signal" in signals.columns else None)
    summaries["signals"]["timeframes"] = sorted(set(signals.get_column("timeframe").to_list())) if signals.height else []
    summaries["signals"]["future_leak_check"] = "manual_review_required"

    out = data_dir / "research/research_quality_report.json"
    write_json(out, summaries)
    return out
