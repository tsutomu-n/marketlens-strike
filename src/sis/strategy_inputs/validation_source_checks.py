from __future__ import annotations

from dataclasses import dataclass
from datetime import timezone
from pathlib import Path
from typing import Any

import polars as pl

from sis.strategy_inputs.models import SourceValidationExpectations
from sis.strategy_inputs.validation_helpers import parse_datetime_value
from sis.strategy_inputs.validation_helpers import serialize_observed_timestamp


@dataclass(frozen=True)
class SourceDataCheckResult:
    valid: bool
    missing_columns: list[str]
    timestamp_check_passed: bool | None
    max_observed_timestamp: str | None
    available_at_column_present: bool | None
    data_error: str | None


def scan_source_frame(path: Path) -> pl.LazyFrame:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return pl.scan_csv(path)
    if suffix in {".jsonl", ".ndjson"}:
        return pl.scan_ndjson(path)
    if suffix == ".parquet":
        return pl.scan_parquet(path)
    raise ValueError(f"column validation supports only CSV, JSONL/NDJSON, or Parquet: {path}")


def source_data_checks(
    *,
    source_path: Path,
    expectations: SourceValidationExpectations | None,
) -> SourceDataCheckResult:
    if expectations is None:
        return SourceDataCheckResult(
            valid=True,
            missing_columns=[],
            timestamp_check_passed=None,
            max_observed_timestamp=None,
            available_at_column_present=None,
            data_error=None,
        )
    try:
        frame = scan_source_frame(source_path)
        columns = set(frame.collect_schema().names())
    except Exception as exc:
        return SourceDataCheckResult(
            valid=False,
            missing_columns=[],
            timestamp_check_passed=None,
            max_observed_timestamp=None,
            available_at_column_present=None,
            data_error=f"failed to read source columns: {exc}",
        )

    expected_columns = set(expectations.required_columns)
    if expectations.timestamp_column is not None:
        expected_columns.add(expectations.timestamp_column)
    if expectations.available_at_column is not None:
        expected_columns.add(expectations.available_at_column)

    missing_columns = sorted(column for column in expected_columns if column not in columns)
    available_at_column_present = (
        None
        if expectations.available_at_column is None
        else expectations.available_at_column in columns
    )
    if missing_columns:
        return SourceDataCheckResult(
            valid=False,
            missing_columns=missing_columns,
            timestamp_check_passed=None,
            max_observed_timestamp=None,
            available_at_column_present=available_at_column_present,
            data_error=None,
        )

    timestamp_check_passed: bool | None = None
    max_observed_timestamp: str | None = None
    if expectations.timestamp_column is not None and expectations.max_allowed_timestamp is not None:
        try:
            result: Any = frame.select(
                pl.col(expectations.timestamp_column).max().alias("max_ts")
            ).collect()
            observed = result["max_ts"][0]
        except Exception as exc:
            return SourceDataCheckResult(
                valid=False,
                missing_columns=[],
                timestamp_check_passed=None,
                max_observed_timestamp=None,
                available_at_column_present=available_at_column_present,
                data_error=f"failed to read timestamp column: {exc}",
            )
        max_observed = parse_datetime_value(observed)
        max_allowed = expectations.max_allowed_timestamp
        if max_allowed.tzinfo is None:
            max_allowed = max_allowed.replace(tzinfo=timezone.utc)
        max_allowed = max_allowed.astimezone(timezone.utc)
        timestamp_check_passed = max_observed is not None and max_observed <= max_allowed
        max_observed_timestamp = serialize_observed_timestamp(max_observed)
        if max_observed is None:
            return SourceDataCheckResult(
                valid=False,
                missing_columns=[],
                timestamp_check_passed=False,
                max_observed_timestamp=None,
                available_at_column_present=available_at_column_present,
                data_error="timestamp column max value is not parseable as datetime",
            )

    return SourceDataCheckResult(
        valid=not missing_columns and (timestamp_check_passed is not False),
        missing_columns=missing_columns,
        timestamp_check_passed=timestamp_check_passed,
        max_observed_timestamp=max_observed_timestamp,
        available_at_column_present=available_at_column_present,
        data_error=None,
    )
