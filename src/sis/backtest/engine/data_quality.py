from __future__ import annotations

from datetime import datetime
from typing import Literal

import polars as pl
from pydantic import BaseModel, Field

from sis.backtest.engine.config import BacktestConfig


class DataQualityReport(BaseModel):
    status: Literal["pass", "warn", "fail"]
    input_row_count: int
    filtered_row_count: int
    first_event_ts: datetime | None = None
    last_event_ts: datetime | None = None
    duplicate_ts_count: int = 0
    duplicate_event_ts_count: int = 0
    out_of_order_count: int = 0
    critical_null_counts: dict[str, int] = Field(default_factory=dict)
    null_critical_field_counts: dict[str, int] = Field(default_factory=dict)
    invalid_price_count: int = 0
    bid_ask_cross_count: int = 0
    cadence_gap_count: int = 0
    symbol_count: int = 0
    coverage_seconds: float | None = None
    median_event_gap_seconds: float | None = None
    max_event_gap_seconds: float | None = None
    bar_count: int = 0
    evaluation_bar_count: int = 0
    insufficient_coverage_for_strategy: bool = False
    required_min_rows: int = 0
    required_min_bars: int = 0
    unknown_fee_mode_count: int = 0
    null_taker_fee_count: int = 0
    null_maker_fee_count: int = 0
    funding_rate_without_interval_count: int = 0
    missing_rate_by_field: dict[str, float] = Field(default_factory=dict)
    fee_unresolved_rate: float = 0.0
    funding_interval_missing_rate: float = 0.0
    oracle_ts_missing_rate: float = 0.0
    raw_payload_ref_missing_rate: float = 0.0
    oi_cap_usage_missing_rate: float = 0.0
    discovery_bound_missing_rate: float = 0.0
    bound_distance_missing_rate: float = 0.0
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


def apply_period_filter(frame: pl.DataFrame, *, config: BacktestConfig) -> pl.DataFrame:
    start = config.period.warmup_start_ts or config.period.evaluation_start_ts
    end = config.period.evaluation_end_ts
    return (
        frame.filter((pl.col("event_ts") >= start) & (pl.col("event_ts") < end))
        .with_columns(
            (pl.col("event_ts") >= config.period.evaluation_start_ts).alias("is_evaluation")
        )
        .sort(["symbol", "event_ts"] if "symbol" in frame.columns else ["event_ts"])
    )


def _missing_required_columns(frame: pl.DataFrame) -> list[str]:
    missing = ["event_ts", "symbol", "is_tradable", "block_reasons"]
    has_price = any(column in frame.columns for column in ("mid_price", "close"))
    has_execution = {"best_bid", "best_ask"}.issubset(
        frame.columns
    ) or "spread_bps" in frame.columns
    has_fee = "taker_fee_bps" in frame.columns or "fee_mode" in frame.columns
    missing = [column for column in missing if column not in frame.columns]
    if not has_price:
        missing.append("mid_price or close")
    if not has_execution:
        missing.append("best_bid/best_ask or spread_bps")
    if not has_fee:
        missing.append("taker_fee_bps or fee_mode")
    return missing


def _critical_null_counts(frame: pl.DataFrame) -> dict[str, int]:
    columns = [
        column
        for column in ("event_ts", "symbol", "is_tradable", "block_reasons")
        if column in frame
    ]
    return {column: int(frame.select(pl.col(column).is_null().sum()).item()) for column in columns}


def _invalid_price_count(frame: pl.DataFrame) -> int:
    columns = [
        column
        for column in ("mid_price", "close", "best_bid", "best_ask", "external_price")
        if column in frame.columns
    ]
    if not columns:
        return 0
    return int(
        frame.select(
            pl.any_horizontal(
                [pl.col(column).is_not_null() & (pl.col(column) <= 0) for column in columns]
            ).sum()
        ).item()
    )


def _bid_ask_cross_count(frame: pl.DataFrame) -> int:
    if not {"best_bid", "best_ask"}.issubset(frame.columns):
        return 0
    return int(
        frame.select(
            (
                pl.col("best_bid").is_not_null()
                & pl.col("best_ask").is_not_null()
                & (pl.col("best_bid") > pl.col("best_ask"))
            ).sum()
        ).item()
    )


def _out_of_order_count(frame: pl.DataFrame) -> int:
    if frame.height <= 1:
        return 0
    sorted_frame = frame.sort(["symbol", "event_ts"])
    original = frame.select(["symbol", "event_ts"]).to_dicts()
    sorted_rows = sorted_frame.select(["symbol", "event_ts"]).to_dicts()
    return sum(1 for left, right in zip(original, sorted_rows, strict=True) if left != right)


def _cadence_gap_count(frame: pl.DataFrame) -> int:
    if frame.height <= 2:
        return 0
    diffs = (
        frame.sort(["symbol", "event_ts"])
        .with_columns(pl.col("event_ts").diff().over("symbol").alias("_gap"))
        .get_column("_gap")
        .drop_nulls()
        .to_list()
    )
    if len(diffs) <= 1:
        return 0
    positive_diffs = [value for value in diffs if value.total_seconds() > 0]
    if not positive_diffs:
        return 0
    expected = min(positive_diffs)
    return sum(1 for value in positive_diffs if value > expected * 1.5)


def _gap_seconds(frame: pl.DataFrame) -> list[float]:
    if frame.height <= 1:
        return []
    values = (
        frame.sort(["symbol", "event_ts"])
        .with_columns(pl.col("event_ts").diff().over("symbol").alias("_gap"))
        .get_column("_gap")
        .drop_nulls()
        .to_list()
    )
    return [float(value.total_seconds()) for value in values if value.total_seconds() > 0]


def _missing_rate(filtered: pl.DataFrame, column: str) -> float:
    if filtered.is_empty() or column not in filtered.columns:
        return 1.0
    return float(filtered.select(pl.col(column).is_null().mean()).item())


def evaluate_data_quality(
    frame: pl.DataFrame,
    *,
    config: BacktestConfig,
    input_row_count: int | None = None,
    required_min_bars: int = 0,
) -> DataQualityReport:
    errors: list[str] = []
    warnings: list[str] = []
    missing = _missing_required_columns(frame)
    if missing:
        errors.append(f"missing required columns: {', '.join(missing)}")
        return DataQualityReport(
            status="fail",
            input_row_count=input_row_count if input_row_count is not None else frame.height,
            filtered_row_count=frame.height,
            errors=errors,
        )

    filtered = apply_period_filter(frame, config=config)
    if filtered.is_empty():
        errors.append("no rows after evaluation filter")

    symbols = (
        set(filtered.get_column("symbol").drop_nulls().to_list()) if "symbol" in filtered else set()
    )
    if symbols and symbols != {config.symbol}:
        errors.append(f"symbol mismatch: expected {config.symbol}, got {sorted(symbols)}")

    critical_null_counts = _critical_null_counts(filtered)
    for column, count in critical_null_counts.items():
        if count:
            errors.append(f"critical nulls in {column}: {count}")

    invalid_price_count = _invalid_price_count(filtered)
    if invalid_price_count:
        errors.append(f"invalid price rows: {invalid_price_count}")

    bid_ask_cross_count = _bid_ask_cross_count(filtered)
    if bid_ask_cross_count:
        errors.append(f"bid/ask crossed rows: {bid_ask_cross_count}")

    fee_columns = [column for column in ("taker_fee_bps", "maker_fee_bps") if column in filtered]
    for column in fee_columns:
        negative_count = int(
            filtered.select((pl.col(column).is_not_null() & (pl.col(column) < 0)).sum()).item()
        )
        if negative_count:
            errors.append(f"negative {column} rows: {negative_count}")
    unknown_fee_mode_count = (
        int(filtered.select((pl.col("fee_mode") == "unknown").sum()).item())
        if "fee_mode" in filtered.columns
        else 0
    )
    if unknown_fee_mode_count:
        warnings.append(f"unknown fee_mode rows: {unknown_fee_mode_count}")
    null_taker_fee_count = (
        int(filtered.select(pl.col("taker_fee_bps").is_null().sum()).item())
        if "taker_fee_bps" in filtered.columns
        else 0
    )
    null_maker_fee_count = (
        int(filtered.select(pl.col("maker_fee_bps").is_null().sum()).item())
        if "maker_fee_bps" in filtered.columns
        else 0
    )
    funding_rate_without_interval_count = (
        int(
            filtered.select(
                (
                    pl.col("funding_rate").is_not_null()
                    & pl.col("funding_interval_minutes").is_null()
                ).sum()
            ).item()
        )
        if {"funding_rate", "funding_interval_minutes"}.issubset(filtered.columns)
        else 0
    )
    if funding_rate_without_interval_count:
        warnings.append(
            "funding_rate present without funding interval assertion: "
            f"{funding_rate_without_interval_count}"
        )
    missing_rate_by_field = {
        column: _missing_rate(filtered, column)
        for column in (
            "raw_payload_ref",
            "oracle_ts_ms",
            "funding_interval_minutes",
            "oi_cap_usage",
            "discovery_bound_pct",
            "bound_distance",
            "taker_fee_bps",
            "maker_fee_bps",
        )
    }
    fee_unresolved_rate = (
        max(missing_rate_by_field["taker_fee_bps"], missing_rate_by_field["maker_fee_bps"])
        if not filtered.is_empty()
        else 1.0
    )

    duplicate_ts_count = (
        filtered.group_by(["symbol", "event_ts"]).len().filter(pl.col("len") > 1).height
    )
    if duplicate_ts_count:
        warnings.append("duplicate event_ts per symbol detected")
    out_of_order_count = _out_of_order_count(filtered)
    if out_of_order_count:
        warnings.append("timestamps are not sorted")
    cadence_gap_count = _cadence_gap_count(filtered)
    if cadence_gap_count:
        warnings.append("cadence gaps detected")

    raw_first_ts = filtered.get_column("event_ts").min() if not filtered.is_empty() else None
    raw_last_ts = filtered.get_column("event_ts").max() if not filtered.is_empty() else None
    first_ts = raw_first_ts if isinstance(raw_first_ts, datetime) else None
    last_ts = raw_last_ts if isinstance(raw_last_ts, datetime) else None
    gap_seconds = _gap_seconds(filtered)
    coverage_seconds = (
        (last_ts - first_ts).total_seconds()
        if first_ts is not None and last_ts is not None
        else None
    )
    unique_symbols = (
        filtered.get_column("symbol").drop_nulls().unique().to_list()
        if "symbol" in filtered.columns
        else []
    )
    bar_count = filtered.height
    evaluation_bar_count = (
        int(filtered.select((pl.col("event_ts") >= config.period.evaluation_start_ts).sum()).item())
        if not filtered.is_empty()
        else 0
    )
    required_min_rows = required_min_bars
    insufficient_coverage = required_min_rows > 0 and filtered.height < required_min_rows
    if insufficient_coverage:
        warnings.append("insufficient coverage for strategy evaluation")
    status: Literal["pass", "warn", "fail"] = "fail" if errors else "warn" if warnings else "pass"
    return DataQualityReport(
        status=status,
        input_row_count=input_row_count if input_row_count is not None else frame.height,
        filtered_row_count=filtered.height,
        first_event_ts=first_ts,
        last_event_ts=last_ts,
        duplicate_ts_count=duplicate_ts_count,
        duplicate_event_ts_count=duplicate_ts_count,
        out_of_order_count=out_of_order_count,
        critical_null_counts=critical_null_counts,
        null_critical_field_counts=critical_null_counts,
        invalid_price_count=invalid_price_count,
        bid_ask_cross_count=bid_ask_cross_count,
        cadence_gap_count=cadence_gap_count,
        symbol_count=len(unique_symbols),
        coverage_seconds=coverage_seconds,
        median_event_gap_seconds=sorted(gap_seconds)[len(gap_seconds) // 2]
        if gap_seconds
        else None,
        max_event_gap_seconds=max(gap_seconds) if gap_seconds else None,
        bar_count=bar_count,
        evaluation_bar_count=evaluation_bar_count,
        insufficient_coverage_for_strategy=insufficient_coverage,
        required_min_rows=required_min_rows,
        required_min_bars=required_min_bars,
        unknown_fee_mode_count=unknown_fee_mode_count,
        null_taker_fee_count=null_taker_fee_count,
        null_maker_fee_count=null_maker_fee_count,
        funding_rate_without_interval_count=funding_rate_without_interval_count,
        missing_rate_by_field=missing_rate_by_field,
        fee_unresolved_rate=fee_unresolved_rate,
        funding_interval_missing_rate=missing_rate_by_field["funding_interval_minutes"],
        oracle_ts_missing_rate=missing_rate_by_field["oracle_ts_ms"],
        raw_payload_ref_missing_rate=missing_rate_by_field["raw_payload_ref"],
        oi_cap_usage_missing_rate=missing_rate_by_field["oi_cap_usage"],
        discovery_bound_missing_rate=missing_rate_by_field["discovery_bound_pct"],
        bound_distance_missing_rate=missing_rate_by_field["bound_distance"],
        warnings=warnings,
        errors=errors,
    )
