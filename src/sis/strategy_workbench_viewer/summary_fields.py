from __future__ import annotations

from typing import Any


STATUS_KEYS = (
    "cycle_status",
    "gate_status",
    "tournament_status",
    "decision_status",
    "plan_status",
    "ingest_status",
    "review_status",
    "status",
    "decision",
    "validation_status",
    "readiness_status",
    "finding_set_status",
    "recommended_action",
)

LATEST_STATUS_AS_ARTIFACT_STATUS_SCHEMAS = frozenset(
    {
        "strategy_case_lite.v1",
        "strategy_case_index.v1",
    }
)

SUMMARY_KEYS = (
    "gate_id",
    "gate_status",
    "cycle_status",
    "human_summary",
    "report_id",
    "tournament_status",
    "leader_action",
    "primary_metric",
    "primary_metric_display_name",
    "cash_metric_basis",
    "actual_cash",
    "event_count",
    "leader_cash_metric_value_usd",
    "leader_actual_cash_result_usd",
    "proxy_gap_count",
    "failed_condition_count",
    "present_stage_count",
    "missing_artifact_path_count",
    "known_gap_count",
    "stop_reason_count",
    "strategy_id",
    "first_observed_at",
    "last_observed_at",
    "pnl_unavailable_reason",
    "proposal_id",
    "review_id",
    "finding_set_id",
    "finding_set_status",
    "source_note_path",
    "source_packet_path",
    "source_note_recommendation",
    "first_finding_type",
    "first_finding_severity",
    "first_finding_impact",
    "first_finding_next_action",
    "decision",
    "decision_id",
    "plan_id",
    "manifest_id",
    "recommended_action",
    "latest_status",
    "open_action_count",
    "pending_human_review_count",
    "boundary_violation_count",
    "scanned_json_count",
    "total_item_count",
    "broken_artifact_count",
    "crypto_perp_gate_follow_up_count",
    "crypto_perp_truth_cycle_follow_up_count",
    "normal_paper_gap_count",
    "drift_review_needed_count",
    "learning_request_pending_count",
    "artifact_count",
    "timeline_count",
    "index_id",
    "case_count",
    "strategy_count",
    "latest_case_path",
    "case_index_source_hash",
    "first_source_artifact_type",
    "first_source_artifact_path",
    "first_source_artifact_schema_version",
    "first_source_artifact_hash",
    "first_brief_item_category",
    "first_brief_item_severity",
    "first_brief_item_status",
    "first_brief_item_schema_version",
    "first_brief_item_action",
    "first_brief_item_reason",
    "first_brief_item_path",
    "ledger_entry_count",
    "paper_order_count",
    "paper_fill_count",
    "no_fill_count",
    "blocked_count",
    "unique_intent_count",
    "unique_symbol_count",
    "max_observed_quote_age_ms",
    "filled_notional_usd_total",
    "max_observed_spread_bps",
    "pnl_available",
    "backtest_passed",
    "trade_count",
    "total_return",
    "max_drawdown",
    "net_pnl_usd",
    "ending_equity_usd",
    "max_drawdown_loss_usd",
    "executed_count",
    "check_count",
    "passed_count",
    "failed_count",
    "pack_artifact_count",
    "suite_method_count",
    "suite_run_count",
    "suite_passed_count",
    "external_result_count",
    "external_engine_run",
    "external_adapters_required_for_completion",
    "standard_engine",
    "suite_id",
    "run_count",
    "method_count",
    "cost_drag_bps",
    "best_run_id",
    "best_run_method_id",
    "best_run_case_id",
    "best_run_total_return",
    "best_run_trade_count",
    "comparison_id",
    "method_result_count",
    "framework_adapter_count",
    "native_total_return",
    "native_trade_count",
    "suite_failed_run_count",
    "threshold_failure_count",
    "suite_best_run_method_id",
    "suite_best_run_case_id",
    "suite_best_run_total_return",
    "suite_best_run_trade_count",
    "weakest_era",
    "weakest_era_total_return",
    "weakest_era_trade_count",
    "portfolio_run_status",
    "portfolio_framework_id",
    "metric_status",
    "metric_framework_id",
    "report_status",
    "report_framework_id",
    "paper_only",
    "live_order_submitted",
    "locked_dependency_added",
    "external_framework_policy_decision",
    "source_proposal_status",
    "proposed_change_count",
    "first_proposed_change_target_section",
    "first_proposed_change_source_reason",
    "first_proposed_change_evidence_summary",
    "approved_change_count",
    "required_action_count",
    "manual_contract_update_input_allowed",
    "requires_human_contract_update",
    "direct_contract_edit_allowed",
    "auto_applied",
    "paper_execution_allowed",
    "live_allowed",
    "first_open_action",
    "first_blocked_reason",
)

SUMMARY_STRING_KEYS = frozenset(
    {
        "gate_id",
        "gate_status",
        "cycle_status",
        "human_summary",
        "report_id",
        "tournament_status",
        "leader_action",
        "primary_metric",
        "primary_metric_display_name",
        "cash_metric_basis",
        "leader_cash_metric_value_usd",
        "strategy_id",
        "first_observed_at",
        "last_observed_at",
        "pnl_unavailable_reason",
        "external_framework_policy_decision",
        "standard_engine",
        "suite_id",
        "best_run_id",
        "best_run_method_id",
        "best_run_case_id",
        "comparison_id",
        "suite_best_run_method_id",
        "suite_best_run_case_id",
        "weakest_era",
        "portfolio_run_status",
        "portfolio_framework_id",
        "metric_status",
        "metric_framework_id",
        "report_status",
        "report_framework_id",
        "proposal_id",
        "review_id",
        "finding_set_id",
        "finding_set_status",
        "source_note_path",
        "source_packet_path",
        "source_note_recommendation",
        "first_finding_type",
        "first_finding_severity",
        "first_finding_impact",
        "first_finding_next_action",
        "decision",
        "decision_id",
        "plan_id",
        "manifest_id",
        "recommended_action",
        "latest_status",
        "first_stop_reason",
        "first_next_step",
        "first_next_step_purpose",
        "first_next_step_command",
        "first_stage_blocker",
        "first_stage_blocker_status",
        "first_stage_blocker_expected_cli_option",
        "first_stage_blocker_expected_artifact_hint",
        "first_stage_blocker_artifact_path",
        "approval_boundary",
        "first_source_artifact_type",
        "first_source_artifact_path",
        "first_source_artifact_schema_version",
        "first_source_artifact_hash",
        "first_brief_item_category",
        "first_brief_item_severity",
        "first_brief_item_status",
        "first_brief_item_schema_version",
        "first_brief_item_action",
        "first_brief_item_reason",
        "first_brief_item_path",
        "index_id",
        "latest_case_path",
        "case_index_source_hash",
        "source_proposal_status",
        "first_proposed_change_target_section",
        "first_proposed_change_source_reason",
        "first_proposed_change_evidence_summary",
        "first_open_action",
        "first_blocked_reason",
    }
)

SUMMARY_INTEGER_KEYS = frozenset(
    {
        "event_count",
        "finding_count",
        "proxy_gap_count",
        "failed_condition_count",
        "present_stage_count",
        "missing_artifact_path_count",
        "known_gap_count",
        "stop_reason_count",
        "open_action_count",
        "pending_human_review_count",
        "boundary_violation_count",
        "scanned_json_count",
        "total_item_count",
        "broken_artifact_count",
        "crypto_perp_gate_follow_up_count",
        "crypto_perp_truth_cycle_follow_up_count",
        "normal_paper_gap_count",
        "drift_review_needed_count",
        "learning_request_pending_count",
        "artifact_count",
        "timeline_count",
        "case_count",
        "strategy_count",
        "proposed_change_count",
        "approved_change_count",
        "required_action_count",
        "ledger_entry_count",
        "paper_order_count",
        "paper_fill_count",
        "no_fill_count",
        "blocked_count",
        "unique_intent_count",
        "unique_symbol_count",
        "max_observed_quote_age_ms",
        "trade_count",
        "executed_count",
        "check_count",
        "passed_count",
        "failed_count",
        "pack_artifact_count",
        "suite_method_count",
        "suite_run_count",
        "suite_passed_count",
        "external_result_count",
        "run_count",
        "method_count",
        "best_run_trade_count",
        "method_result_count",
        "framework_adapter_count",
        "native_trade_count",
        "suite_failed_run_count",
        "threshold_failure_count",
        "suite_best_run_trade_count",
        "weakest_era_trade_count",
    }
)

SUMMARY_NUMBER_KEYS = frozenset(
    {
        "leader_actual_cash_result_usd",
        "filled_notional_usd_total",
        "max_observed_spread_bps",
        "total_return",
        "max_drawdown",
        "net_pnl_usd",
        "ending_equity_usd",
        "max_drawdown_loss_usd",
        "cost_drag_bps",
        "best_run_total_return",
        "native_total_return",
        "suite_best_run_total_return",
        "weakest_era_total_return",
    }
)

SUMMARY_BOOLEAN_KEYS = frozenset(
    {
        "first_next_step_requires_explicit_approval",
        "backtest_passed",
        "paper_only",
        "live_order_submitted",
        "locked_dependency_added",
        "external_engine_run",
        "external_adapters_required_for_completion",
        "manual_contract_update_input_allowed",
        "requires_human_contract_update",
        "direct_contract_edit_allowed",
        "auto_applied",
        "paper_execution_allowed",
        "live_allowed",
        "pnl_available",
        "actual_cash",
    }
)

SUMMARY_FALSE_ONLY_KEYS = frozenset(
    {
        "first_next_step_network_allowed",
        "first_next_step_exchange_write_allowed",
        "first_next_step_live_order_allowed",
    }
)


def _first_status(payload: dict[str, Any]) -> str | None:
    for key in STATUS_KEYS:
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def artifact_status(payload: dict[str, Any], summary: dict[str, Any]) -> str | None:
    status = _first_status(payload)
    if status is not None:
        return status
    if payload.get("schema_version") in LATEST_STATUS_AS_ARTIFACT_STATUS_SCHEMAS:
        latest_status = summary.get("latest_status")
        if isinstance(latest_status, str) and latest_status:
            return latest_status
    return None


def _compact_summary_value(key: str, value: Any) -> str | int | float | bool | None:
    if key in SUMMARY_STRING_KEYS:
        return value if isinstance(value, str) else None
    if key in SUMMARY_INTEGER_KEYS:
        return value if isinstance(value, int) and not isinstance(value, bool) else None
    if key in SUMMARY_NUMBER_KEYS:
        return value if isinstance(value, int | float) and not isinstance(value, bool) else None
    if key in SUMMARY_BOOLEAN_KEYS:
        return value if isinstance(value, bool) else None
    if key in SUMMARY_FALSE_ONLY_KEYS:
        return value if value is False else None
    if isinstance(value, str | int | float | bool):
        return value
    return None


def _set_compact_summary_value(summary: dict[str, Any], key: str, value: Any) -> None:
    compact_value = _compact_summary_value(key, value)
    if compact_value is not None and key not in summary:
        summary[key] = compact_value


def _set_compact_summary_values(
    summary: dict[str, Any],
    source: dict[str, Any],
    pairs: tuple[tuple[str, str], ...],
) -> None:
    for source_key, summary_key in pairs:
        _set_compact_summary_value(summary, summary_key, source.get(source_key))
