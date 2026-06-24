from __future__ import annotations

from typing import Any

from sis.venues.trade_xyz.collection_status_report import render_collection_status_report


def _status(next_actions: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "decision": "COLLECT_MORE_QUOTES",
        "backtest_data_ready": False,
        "readiness_decision": "NO_GO",
        "fail_count": 1,
        "known_gap_count": 1,
        "latest_file_stale": True,
        "collector_process": {"running": False, "process_count": 0},
        "supervisor_process": {"running": False, "process_count": 0},
        "locks": {
            "cycle": {"stale": True},
            "supervisor": {"stale": False},
        },
        "runtime_prerequisites": {
            "aws_cli": {"available": False, "source": "missing"},
            "lz4": {"available": True},
        },
        "historical_archive_preflight": {"status": "fail", "return_code": 1},
        "historical_archive_artifacts": {
            "bulk_plan": {"exists": True, "estimated_total_object_count": 90},
            "bulk_execution": {
                "status": "planned",
                "dry_run": True,
                "selected_object_count": 10,
                "downloaded_object_count": 0,
                "command_error_count": 0,
            },
            "bulk_normalization": {
                "status": "completed",
                "normalized_file_count": 1,
            },
        },
        "ws_artifacts": {
            "capture": {
                "exists": False,
                "row_count": None,
                "error_count": None,
                "reconnect_count": None,
            },
            "quality": {"exists": False, "status": None, "row_count": None},
            "rest_parity": {
                "exists": False,
                "status": None,
                "missing_rest_symbols": ["NVDA"],
            },
        },
        "account_fee_prerequisites": {"configured": False},
        "account_fee_artifact": {
            "exists": True,
            "status": "pass",
            "matches_configured_user": None,
            "user_taker_fee_bps": 9.0,
            "user_maker_fee_bps": 3.0,
        },
        "progress_since_previous_status": {
            "status": "warning",
            "traceable_row_count_delta": 0,
        },
        "raw_quote_inventory": {
            "latest_file_age_seconds": 4000.0,
            "traceable_row_count": 2,
            "untraceable_row_count": 1,
            "malformed_row_count": 2,
            "missing_symbol_row_count": 1,
            "symbol_counts": {"NVDA": 1, "SP500": 1, "<missing>": 1},
            "source_counts": {"trade_xyz_l2Book": 3},
        },
        "next_actions": next_actions,
    }


def test_render_collection_status_report_preserves_key_lines_and_commands() -> None:
    report = render_collection_status_report(
        status=_status(
            [
                {
                    "key": "historical_archive_backfill",
                    "status": "blocked_by_prerequisites",
                    "blocked_by": ["missing_aws_command"],
                    "plan_command": "uv run sis plan-trade-xyz-historical-archive-bulk",
                    "command": "uv run sis execute-trade-xyz-historical-archive-bulk --max-objects 10",
                    "execute_command": (
                        "uv run sis execute-trade-xyz-historical-archive-bulk "
                        "--execute --acknowledge-requester-pays"
                    ),
                    "env_var": "SIS_TRADE_XYZ_ACCOUNT_FEE_USER_ADDRESS",
                    "env_configured": False,
                    "user_address_sha256": "abc123",
                }
            ]
        ),
        progress={
            "coverage_passed": False,
            "min_span_days": 0.0,
            "max_remaining_days_exact": 30.0,
            "completion_ratio_by_span": 0.25,
            "slowest_symbols": ["NVDA"],
        },
        readiness_requirements={
            "fail": ["quote_coverage"],
            "known_gap": ["account_specific_fee"],
        },
        readiness_details={
            "funding_events": {"status": "known_gap", "skipped": {"reason": "missing"}},
            "oracle_timestamp_provenance": {
                "status": "fail",
                "oracle_ts_missing_rate": 1.0,
                "oracle_freshness_proxy": {"observed_rate": 0.8},
            },
            "signal_candles": {
                "status": "pass",
                "missing_symbols": [],
                "missing_intervals": [],
                "request_error_count": 0,
            },
        },
    )

    assert "failing_requirements: quote_coverage" in report
    assert "raw_symbol_counts: <missing>:1,NVDA:1,SP500:1" in report
    assert "historical_archive_bulk_execution_status: planned" in report
    assert "- plan_command: `uv run sis plan-trade-xyz-historical-archive-bulk`" in report
    assert "--execute --acknowledge-requester-pays" in report
    assert "user_address_sha256: abc123" in report


def test_render_collection_status_report_handles_empty_next_actions() -> None:
    report = render_collection_status_report(
        status=_status([]),
        progress={
            "coverage_passed": True,
            "min_span_days": 30.0,
            "max_remaining_days_exact": 0.0,
            "completion_ratio_by_span": 1.0,
            "slowest_symbols": [],
        },
        readiness_requirements={"fail": [], "known_gap": []},
        readiness_details={},
    )

    assert "## Next Actions" in report
    assert "- none" in report
