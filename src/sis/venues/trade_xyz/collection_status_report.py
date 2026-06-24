from __future__ import annotations

from typing import Any

from sis.venues.trade_xyz.collection_status_progress import format_counts


def render_collection_status_report(
    *,
    status: dict[str, Any],
    progress: dict[str, Any],
    readiness_requirements: dict[str, list[str]],
    readiness_details: dict[str, Any],
) -> str:
    lines = [
        "# Trade[XYZ] Collection Status",
        "",
        f"- decision: {status['decision']}",
        f"- backtest_data_ready: {status['backtest_data_ready']}",
        f"- readiness_decision: {status['readiness_decision']}",
        f"- fail_count: {status['fail_count']}",
        f"- known_gap_count: {status['known_gap_count']}",
        f"- failing_requirements: {','.join(readiness_requirements['fail'])}",
        f"- known_gap_requirements: {','.join(readiness_requirements['known_gap'])}",
        f"- funding_events_status: {readiness_details.get('funding_events', {}).get('status')}",
        f"- funding_events_skipped: {readiness_details.get('funding_events', {}).get('skipped')}",
        "- oracle_timestamp_provenance_status: "
        f"{readiness_details.get('oracle_timestamp_provenance', {}).get('status')}",
        "- oracle_ts_missing_rate: "
        f"{readiness_details.get('oracle_timestamp_provenance', {}).get('oracle_ts_missing_rate')}",
        "- oracle_freshness_proxy_observed_rate: "
        f"{(readiness_details.get('oracle_timestamp_provenance', {}).get('oracle_freshness_proxy') or {}).get('observed_rate')}",
        f"- signal_candles_status: {readiness_details.get('signal_candles', {}).get('status')}",
        "- signal_candles_missing_symbols: "
        f"{','.join(readiness_details.get('signal_candles', {}).get('missing_symbols') or [])}",
        "- signal_candles_missing_intervals: "
        f"{','.join(readiness_details.get('signal_candles', {}).get('missing_intervals') or [])}",
        "- signal_candles_request_error_count: "
        f"{readiness_details.get('signal_candles', {}).get('request_error_count')}",
        f"- coverage_passed: {progress['coverage_passed']}",
        f"- latest_file_stale: {status['latest_file_stale']}",
        f"- collector_running: {status['collector_process']['running']}",
        f"- collector_process_count: {status['collector_process']['process_count']}",
        f"- supervisor_running: {status['supervisor_process']['running']}",
        f"- supervisor_process_count: {status['supervisor_process']['process_count']}",
        f"- cycle_lock_stale: {status['locks']['cycle']['stale']}",
        f"- supervisor_lock_stale: {status['locks']['supervisor']['stale']}",
        f"- aws_cli_available: {status['runtime_prerequisites']['aws_cli']['available']}",
        f"- aws_command_source: {status['runtime_prerequisites']['aws_cli']['source']}",
        f"- historical_archive_preflight_status: {status['historical_archive_preflight']['status']}",
        f"- historical_archive_preflight_return_code: {status['historical_archive_preflight']['return_code']}",
        "- historical_archive_bulk_plan_exists: "
        f"{status['historical_archive_artifacts']['bulk_plan']['exists']}",
        "- historical_archive_bulk_plan_estimated_total_object_count: "
        f"{status['historical_archive_artifacts']['bulk_plan']['estimated_total_object_count']}",
        "- historical_archive_bulk_execution_status: "
        f"{status['historical_archive_artifacts']['bulk_execution']['status']}",
        "- historical_archive_bulk_execution_dry_run: "
        f"{status['historical_archive_artifacts']['bulk_execution']['dry_run']}",
        "- historical_archive_bulk_execution_selected_object_count: "
        f"{status['historical_archive_artifacts']['bulk_execution']['selected_object_count']}",
        "- historical_archive_bulk_execution_downloaded_object_count: "
        f"{status['historical_archive_artifacts']['bulk_execution']['downloaded_object_count']}",
        "- historical_archive_bulk_execution_command_error_count: "
        f"{status['historical_archive_artifacts']['bulk_execution']['command_error_count']}",
        "- historical_archive_bulk_normalization_status: "
        f"{status['historical_archive_artifacts']['bulk_normalization']['status']}",
        "- historical_archive_bulk_normalization_normalized_file_count: "
        f"{status['historical_archive_artifacts']['bulk_normalization']['normalized_file_count']}",
        f"- ws_capture_manifest_exists: {status['ws_artifacts']['capture']['exists']}",
        f"- ws_capture_row_count: {status['ws_artifacts']['capture']['row_count']}",
        f"- ws_capture_error_count: {status['ws_artifacts']['capture']['error_count']}",
        f"- ws_capture_reconnect_count: {status['ws_artifacts']['capture']['reconnect_count']}",
        f"- ws_quality_manifest_exists: {status['ws_artifacts']['quality']['exists']}",
        f"- ws_quality_status: {status['ws_artifacts']['quality']['status']}",
        f"- ws_quality_row_count: {status['ws_artifacts']['quality']['row_count']}",
        f"- ws_rest_parity_manifest_exists: {status['ws_artifacts']['rest_parity']['exists']}",
        f"- ws_rest_parity_status: {status['ws_artifacts']['rest_parity']['status']}",
        "- ws_rest_parity_missing_rest_symbols: "
        f"{','.join(status['ws_artifacts']['rest_parity']['missing_rest_symbols'])}",
        f"- lz4_available: {status['runtime_prerequisites']['lz4']['available']}",
        f"- account_fee_user_address_configured: {status['account_fee_prerequisites']['configured']}",
        f"- account_fee_manifest_exists: {status['account_fee_artifact']['exists']}",
        f"- account_fee_manifest_status: {status['account_fee_artifact']['status']}",
        f"- account_fee_manifest_user_matches_env: {status['account_fee_artifact']['matches_configured_user']}",
        f"- account_fee_user_taker_fee_bps: {status['account_fee_artifact']['user_taker_fee_bps']}",
        f"- account_fee_user_maker_fee_bps: {status['account_fee_artifact']['user_maker_fee_bps']}",
        f"- progress_status: {status['progress_since_previous_status']['status']}",
        "- traceable_row_count_delta: "
        f"{status['progress_since_previous_status']['traceable_row_count_delta']}",
        f"- latest_file_age_seconds: {status['raw_quote_inventory']['latest_file_age_seconds']}",
        f"- traceable_rows: {status['raw_quote_inventory']['traceable_row_count']}",
        f"- untraceable_rows: {status['raw_quote_inventory']['untraceable_row_count']}",
        f"- malformed_rows: {status['raw_quote_inventory']['malformed_row_count']}",
        f"- missing_symbol_rows: {status['raw_quote_inventory']['missing_symbol_row_count']}",
        f"- raw_symbol_counts: {format_counts(status['raw_quote_inventory']['symbol_counts'])}",
        f"- raw_source_counts: {format_counts(status['raw_quote_inventory']['source_counts'])}",
        f"- coverage_min_span_days: {progress['min_span_days']}",
        f"- coverage_max_remaining_days_exact: {progress['max_remaining_days_exact']}",
        f"- coverage_completion_ratio_by_span: {progress['completion_ratio_by_span']}",
        f"- coverage_slowest_symbols: {','.join(progress['slowest_symbols'])}",
        "",
        "## Next Actions",
        "",
    ]
    if status["next_actions"]:
        for action in status["next_actions"]:
            lines.append(f"- key: {action['key']}")
            if action.get("status") is not None:
                lines.append(f"  - status: {action['status']}")
            if action.get("blocked_by"):
                lines.append(f"  - blocked_by: {','.join(action['blocked_by'])}")
            for command_key in (
                "plan_command",
                "preflight_command",
                "preflight_status",
                "preflight_return_code",
                "dry_run_command",
                "execute_command",
                "command",
                "follow_up_command",
                "final_check_command",
            ):
                command_value = action.get(command_key)
                if command_value:
                    lines.append(f"  - {command_key}: `{command_value}`")
            if action.get("env_var"):
                lines.append(f"  - env_var: {action['env_var']}")
                lines.append(f"  - env_configured: {action.get('env_configured')}")
            if action.get("user_address_sha256"):
                lines.append(f"  - user_address_sha256: {action['user_address_sha256']}")
    else:
        lines.append("- none")
    return "\n".join(lines) + "\n"
