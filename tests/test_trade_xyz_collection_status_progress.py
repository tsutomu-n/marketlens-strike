from datetime import UTC, datetime

from sis.venues.trade_xyz.collection_status_progress import coverage_progress
from sis.venues.trade_xyz.collection_status_progress import cycle_command
from sis.venues.trade_xyz.collection_status_progress import format_counts
from sis.venues.trade_xyz.collection_status_progress import parse_generated_at
from sis.venues.trade_xyz.collection_status_progress import progress_since_previous


def test_coverage_progress_reports_missing_manifest_defaults() -> None:
    progress = coverage_progress(None)

    assert progress == {
        "coverage_passed": False,
        "reason": "missing trade_xyz_quote_coverage_manifest.json",
        "symbols": {},
        "estimated_max_collection_days_required": None,
        "min_span_days": None,
        "max_span_days": None,
        "max_remaining_days_exact": None,
        "completion_ratio_by_span": None,
        "slowest_symbols": [],
    }


def test_coverage_progress_summarizes_symbol_remaining_days() -> None:
    progress = coverage_progress(
        {
            "coverage_passed": False,
            "traceable_only": True,
            "row_count": 30,
            "raw_row_count": 32,
            "excluded_missing_raw_payload_ref_count": 2,
            "raw_payload_ref_missing_rate_all_rows": 0.0625,
            "per_symbol": {
                "NVDA": {
                    "coverage_status": "pass",
                    "row_count": 20,
                    "raw_row_count": 20,
                    "span_days": 30.0,
                    "min_days_required": 30.0,
                    "max_gap_seconds": 60.0,
                    "insufficient_reasons": [],
                    "missing_rates": {"oracle": 0.0},
                    "excluded_missing_raw_payload_ref_count": 0,
                },
                "SPY": {
                    "coverage_status": "insufficient",
                    "row_count": 10,
                    "raw_row_count": 12,
                    "span_days": 12.25,
                    "min_days_required": 30.0,
                    "max_gap_seconds": 120.0,
                    "insufficient_reasons": ["span_days_below_min"],
                    "missing_rates": {"oracle": 0.2},
                    "excluded_missing_raw_payload_ref_count": 2,
                },
            },
        }
    )

    assert progress["coverage_passed"] is False
    assert progress["traceable_only"] is True
    assert progress["estimated_max_collection_days_required"] == 18
    assert progress["min_span_days"] == 12.25
    assert progress["max_span_days"] == 30.0
    assert progress["max_remaining_days_exact"] == 17.75
    assert progress["completion_ratio_by_span"] == 30.0 / 47.75
    assert progress["slowest_symbols"] == ["SPY"]
    assert progress["symbols"]["SPY"]["estimated_collection_days_required"] == 18


def test_parse_generated_at_normalizes_valid_values_and_ignores_invalid_values() -> None:
    assert parse_generated_at("2026-05-31T09:00:00+09:00") == datetime(
        2026, 5, 31, 0, 0, tzinfo=UTC
    )
    assert parse_generated_at("2026-05-31T00:00:00") == datetime(2026, 5, 31, 0, 0, tzinfo=UTC)
    assert parse_generated_at("") is None
    assert parse_generated_at("not-a-date") is None
    assert parse_generated_at(None) is None


def test_progress_since_previous_reports_warning_cases() -> None:
    generated_at = datetime(2026, 5, 31, 0, 3, tzinfo=UTC)

    missing = progress_since_previous(
        None,
        generated_at=generated_at,
        raw_inventory={"row_count": 2, "traceable_row_count": 2},
        coverage={"coverage_passed": False},
        collector_process={"running": True},
        latest_file_stale=False,
        interval_seconds=60,
    )

    assert missing["previous_status_exists"] is False
    assert missing["status"] == "unknown_no_previous_status"
    assert missing["warnings"] == []

    warning = progress_since_previous(
        {
            "generated_at": "2026-05-31T00:00:00+00:00",
            "raw_quote_inventory": {"row_count": 2, "traceable_row_count": 2},
        },
        generated_at=generated_at,
        raw_inventory={"row_count": 3, "traceable_row_count": 2},
        coverage={"coverage_passed": False},
        collector_process={"running": True},
        latest_file_stale=True,
        interval_seconds=60,
    )

    assert warning["previous_status_exists"] is True
    assert warning["seconds_since_previous_status"] == 180.0
    assert warning["row_count_delta"] == 1
    assert warning["traceable_row_count_delta"] == 0
    assert warning["status"] == "warning"
    assert warning["warnings"] == [
        "latest_file_stale",
        "no_traceable_row_growth_since_previous_status",
    ]

    stopped = progress_since_previous(
        {
            "generated_at": "2026-05-31T00:00:00+00:00",
            "raw_quote_inventory": {"row_count": 1, "traceable_row_count": 1},
        },
        generated_at=generated_at,
        raw_inventory={"row_count": 2, "traceable_row_count": 2},
        coverage={"coverage_passed": False},
        collector_process={"running": False},
        latest_file_stale=False,
        interval_seconds=60,
    )

    assert stopped["status"] == "warning"
    assert stopped["warnings"] == ["collector_not_running_while_coverage_incomplete"]


def test_cycle_command_and_format_counts_preserve_report_text() -> None:
    assert format_counts({"SPY": 2, "NVDA": 1}) == "NVDA:1,SPY:2"

    command = cycle_command(["NVDA", "SPY"], duration_minutes=1440, interval_seconds=60)

    assert command == (
        "uv run sis collect-trade-xyz-data-cycle "
        "--collection-config configs/trade_xyz_data_collection.yaml "
        "--duration-minutes 1440 --interval-seconds 60 --symbols NVDA,SPY"
    )
