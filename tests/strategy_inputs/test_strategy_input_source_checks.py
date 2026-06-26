from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from sis.strategy_inputs.models import SourceValidationExpectations
from sis.strategy_inputs.validation_source_checks import source_data_checks


def test_source_data_checks_passes_without_expectations(tmp_path: Path) -> None:
    result = source_data_checks(source_path=tmp_path / "missing.csv", expectations=None)

    assert result.valid is True
    assert result.missing_columns == []
    assert result.timestamp_check_passed is None
    assert result.max_observed_timestamp is None
    assert result.available_at_column_present is None
    assert result.data_error is None


def test_source_data_checks_reports_missing_required_and_available_at_columns(
    tmp_path: Path,
) -> None:
    source_path = tmp_path / "ohlcv.csv"
    source_path.write_text("ts,close\n2026-06-18T12:00:00Z,1\n", encoding="utf-8")

    result = source_data_checks(
        source_path=source_path,
        expectations=SourceValidationExpectations(
            required_columns=["close", "spread_bps"],
            available_at_column="available_at",
            available_at_column_required=True,
        ),
    )

    assert result.valid is False
    assert result.missing_columns == ["available_at", "spread_bps"]
    assert result.available_at_column_present is False
    assert result.timestamp_check_passed is None
    assert result.max_observed_timestamp is None
    assert result.data_error is None


def test_source_data_checks_detects_future_timestamp(tmp_path: Path) -> None:
    source_path = tmp_path / "ohlcv.csv"
    source_path.write_text("ts,close\n2026-06-19T12:00:00Z,1\n", encoding="utf-8")

    result = source_data_checks(
        source_path=source_path,
        expectations=SourceValidationExpectations(
            required_columns=["close"],
            timestamp_column="ts",
            max_allowed_timestamp=datetime(2026, 6, 18, 12, tzinfo=timezone.utc),
        ),
    )

    assert result.valid is False
    assert result.missing_columns == []
    assert result.timestamp_check_passed is False
    assert result.max_observed_timestamp == "2026-06-19T12:00:00Z"
    assert result.data_error is None


def test_source_data_checks_returns_data_error_for_unsupported_suffix(tmp_path: Path) -> None:
    source_path = tmp_path / "ohlcv.txt"
    source_path.write_text("ts,close\n2026-06-18T12:00:00Z,1\n", encoding="utf-8")

    result = source_data_checks(
        source_path=source_path,
        expectations=SourceValidationExpectations(required_columns=["close"]),
    )

    assert result.valid is False
    assert result.missing_columns == []
    assert result.data_error is not None
    assert "column validation supports only CSV" in result.data_error
