from __future__ import annotations

from pathlib import Path

from sis.reports.doc_paths import recommended_read_order
from sis.reports.loaders import normalized_summary, safe_read_json_dict
from sis.reports.summary_normalizers import (
    audit_summary_fields,
    audit_bundle_history_flat_fields,
    audit_dashboard_flat_fields,
    audit_timeline_flat_fields,
    execution_comparison_flat_fields,
    execution_diagnostics_flat_fields,
    execution_gap_history_flat_fields,
    execution_snapshot_flat_fields,
    execution_snapshot_drift_flat_fields,
    execution_state_comparison_flat_fields,
    execution_drift_overview_flat_fields,
    normalize_execution_comparison_summary,
    normalize_execution_diagnostics_summary,
    normalize_execution_gap_history_summary,
    normalize_execution_snapshot_drift_summary,
    normalize_execution_snapshot_summary,
    normalize_execution_state_comparison_summary,
    normalize_execution_drift_overview_summary,
    latest_execution_lineage_flat_lines,
    normalize_phase_gate_summary,
    merged_latest_execution_lineage_fields,
    phase_gate_flat_fields,
    phase_gate_issue_preview_lines,
)
from sis.storage.jsonl_store import write_json


def _report_path_for_summary(path: Path | None, report_name: str) -> str | None:
    if path is None:
        return None
    base = path.parent.parent if path.parent.name == "ops" else path.parent
    return str(base / "reports" / report_name)


def _live_evidence_report_path(
    summary_path: Path | None,
    live_evidence_summary: dict[str, object] | None = None,
) -> str | None:
    run_id = None
    if isinstance(live_evidence_summary, dict):
        run_id = live_evidence_summary.get("run_id")
    if not isinstance(run_id, str) or not run_id:
        if summary_path is None:
            return None
        stem = summary_path.stem
        prefix = "live_evidence_summary_"
        if not stem.startswith(prefix):
            return None
        run_id = stem[len(prefix) :]
    return str(Path("docs/live_evidence_reports") / f"live_evidence_report_{run_id}.md")


def _related_reports(
    restart_pointers: dict[str, object],
    phase_gate_review_report_path: object,
) -> dict[str, str]:
    ordered_items = (
        ("current_state_index_report", restart_pointers.get("current_state_index_report")),
        ("readiness_snapshot_report", restart_pointers.get("readiness_snapshot_report")),
        ("phase_gate_review_report", phase_gate_review_report_path),
        ("remediation_scoreboard_report", restart_pointers.get("remediation_scoreboard_report")),
        (
            "remediation_session_checkpoint_report",
            restart_pointers.get("remediation_session_checkpoint_report"),
        ),
        ("remediation_session_report", restart_pointers.get("remediation_session_report")),
        (
            "remediation_execution_plan_report",
            restart_pointers.get("remediation_execution_plan_report"),
        ),
        ("remediation_planner_report", restart_pointers.get("remediation_planner_report")),
        ("remediation_evaluator_report", restart_pointers.get("remediation_evaluator_report")),
        ("remediation_evidence_report", restart_pointers.get("remediation_evidence_report")),
        (
            "remediation_command_results_report",
            restart_pointers.get("remediation_command_results_report"),
        ),
        ("live_evidence_report", restart_pointers.get("live_evidence_report")),
    )
    return {
        key: value
        for key, value in ordered_items
        if isinstance(value, str) and value
    }


def _quick_navigation(
    restart_pointers: dict[str, object],
    phase_gate_review_report_path: object,
) -> dict[str, str]:
    items = (
        ("current_state_index_report", restart_pointers.get("current_state_index_report")),
        ("readiness_snapshot_report", restart_pointers.get("readiness_snapshot_report")),
        ("phase_gate_review_report", phase_gate_review_report_path),
        ("remediation_scoreboard_report", restart_pointers.get("remediation_scoreboard_report")),
        ("live_evidence_report", restart_pointers.get("live_evidence_report")),
    )
    return {
        key: value
        for key, value in items
        if isinstance(value, str) and value
    }


def build_current_state_index(
    *,
    operations_dashboard_summary_path: Path | None = None,
    operations_bundle_manifest_path: Path | None = None,
    audit_dashboard_summary_path: Path | None = None,
    audit_bundle_manifest_path: Path | None = None,
    phase_gate_summary_path: Path | None = None,
    execution_snapshot_summary_path: Path | None = None,
    execution_venue_comparison_summary_path: Path | None = None,
    execution_venue_diagnostics_summary_path: Path | None = None,
    execution_gap_history_summary_path: Path | None = None,
    execution_state_comparison_history_summary_path: Path | None = None,
    execution_snapshot_drift_history_summary_path: Path | None = None,
    execution_drift_overview_summary_path: Path | None = None,
    backtest_metrics_summary_path: Path | None = None,
    live_evidence_summary_path: Path | None = None,
    research_quality_report_path: Path | None = None,
    out_path: Path | None = None,
    summary_path: Path | None = None,
) -> str:
    operations_dashboard = safe_read_json_dict(operations_dashboard_summary_path)
    operations_bundle = safe_read_json_dict(operations_bundle_manifest_path)
    audit_dashboard = safe_read_json_dict(audit_dashboard_summary_path)
    audit_bundle = safe_read_json_dict(audit_bundle_manifest_path)
    phase_gate = normalized_summary(phase_gate_summary_path, normalize_phase_gate_summary)
    execution_snapshot = normalized_summary(
        execution_snapshot_summary_path,
        normalize_execution_snapshot_summary,
    )
    execution_comparison = normalized_summary(
        execution_venue_comparison_summary_path,
        normalize_execution_comparison_summary,
    )
    execution_diagnostics = normalized_summary(
        execution_venue_diagnostics_summary_path,
        normalize_execution_diagnostics_summary,
    )
    execution_gap_history = normalized_summary(
        execution_gap_history_summary_path,
        normalize_execution_gap_history_summary,
    )
    execution_state_comparison_history = normalized_summary(
        execution_state_comparison_history_summary_path,
        normalize_execution_state_comparison_summary,
    )
    execution_snapshot_drift_history = normalized_summary(
        execution_snapshot_drift_history_summary_path,
        normalize_execution_snapshot_drift_summary,
    )
    execution_drift_overview = normalized_summary(
        execution_drift_overview_summary_path,
        normalize_execution_drift_overview_summary,
    )
    execution_snapshot_fields = execution_snapshot_flat_fields(execution_snapshot)
    execution_comparison_fields = execution_comparison_flat_fields(execution_comparison)
    execution_diagnostics_fields = execution_diagnostics_flat_fields(execution_diagnostics)
    execution_gap_history_fields = execution_gap_history_flat_fields(execution_gap_history)
    execution_state_comparison_fields = execution_state_comparison_flat_fields(
        execution_state_comparison_history
    )
    execution_snapshot_drift_fields = execution_snapshot_drift_flat_fields(
        execution_snapshot_drift_history
    )
    phase_gate_fields = phase_gate_flat_fields(phase_gate)
    execution_drift_fields = execution_drift_overview_flat_fields(execution_drift_overview)
    audit_dashboard_fields = audit_dashboard_flat_fields(audit_dashboard)
    audit_timeline_fields = audit_timeline_flat_fields(audit_dashboard)
    audit_bundle_history_fields = audit_bundle_history_flat_fields(audit_bundle)
    audit_summary = audit_summary_fields(audit_dashboard, audit_bundle)
    latest_execution_lineage = merged_latest_execution_lineage_fields(
        audit_dashboard,
        audit_bundle,
        operations_bundle,
    )
    execution_adapter_fields = {
        key: operations_dashboard.get(key)
        for key in (
            "execution_balance_status_venue",
            "execution_balance_status_currency",
            "execution_balance_status_equity",
            "execution_balance_status_available_cash",
            "execution_balance_status_margin_used",
            "execution_balance_status_notional_usd",
            "execution_balance_status_unrealized_pnl",
            "execution_balance_status_cumulative_rollover_usd",
            "execution_balance_status_snapshot_exists",
            "execution_balance_status_report_path",
            "execution_fill_status_venue",
            "execution_fill_status_fills_count",
            "execution_fill_status_latest_fill_id",
            "execution_fill_status_latest_fill_order_id",
            "execution_fill_status_latest_fill_symbol",
            "execution_fill_status_latest_fill_side",
            "execution_fill_status_latest_fill_quantity",
            "execution_fill_status_latest_fill_price",
            "execution_fill_status_latest_fill_status",
            "execution_fill_status_latest_fill_ts_fill",
            "execution_fill_status_report_path",
            "execution_order_status_venue",
            "execution_order_status_order_id",
            "execution_order_status_status",
            "execution_order_status_symbol",
            "execution_order_status_side",
            "execution_order_status_quantity",
            "execution_order_status_report_path",
            "execution_cancel_order_target",
            "execution_cancel_order_status",
            "execution_cancel_order_report_path",
            "execution_close_position_target",
            "execution_close_position_status",
            "execution_close_position_report_path",
            "execution_reconcile_positions_matched",
            "execution_reconcile_positions_missing_in_adapter_count",
            "execution_reconcile_positions_missing_in_internal_count",
            "execution_reconcile_positions_report_path",
            "execution_read_only_surfaces_venue_count",
            "execution_read_only_surfaces_with_balance_snapshot_count",
            "execution_read_only_surfaces_with_positions_snapshot_count",
            "execution_read_only_surfaces_with_fills_snapshot_count",
            "execution_read_only_surfaces_with_order_status_snapshot_count",
            "execution_read_only_surfaces_reconciled_venue_count",
            "execution_read_only_surfaces_with_positions_financial_totals_count",
            "execution_read_only_surfaces_with_positions_rollover_metrics_count",
            "execution_read_only_surfaces_with_positions_protection_metrics_count",
            "execution_read_only_surfaces_with_positions_leverage_metrics_count",
            "execution_read_only_surfaces_with_positions_return_metrics_count",
            "execution_read_only_surfaces_with_positions_day_trade_metrics_count",
            "execution_read_only_surfaces_with_positions_limit_metrics_count",
            "execution_read_only_surfaces_with_positions_quantity_metrics_count",
            "execution_read_only_surfaces_positions_notional_usd_total",
            "execution_read_only_surfaces_positions_unrealized_pnl_usd_total",
            "execution_read_only_surfaces_positions_collateral_used_usd_total",
            "execution_read_only_surfaces_positions_max_withdrawable_usd_total",
            "execution_read_only_surfaces_positions_cumulative_rollover_usd_total",
            "execution_read_only_surfaces_positions_with_liquidation_price_count",
            "execution_read_only_surfaces_positions_with_take_profit_count",
            "execution_read_only_surfaces_positions_with_stop_loss_count",
            "execution_read_only_surfaces_positions_day_trade_count",
            "execution_read_only_surfaces_positions_average_leverage",
            "execution_read_only_surfaces_positions_average_return_on_equity",
            "execution_read_only_surfaces_positions_max_leverage",
            "execution_read_only_surfaces_positions_total_quantity",
            "execution_read_only_surfaces_positions_total_realized_pnl",
            "execution_read_only_surfaces_latest_positions_server_time_ms",
            "execution_read_only_surfaces_latest_positions_open_timestamp_ms",
            "execution_read_only_surfaces_latest_positions_updated_at",
            "execution_read_only_surfaces_latest_positions_client_ts",
            "execution_read_only_surfaces_report_path",
            "daemon_manifest_mode",
            "daemon_manifest_command",
            "daemon_manifest_state_store_path",
            "daemon_manifest_report_path",
            "state_export_snapshot_path",
            "state_export_audit_overall_status",
            "state_export_phase_gate_decision",
            "state_export_readiness_next_phase_candidate",
            "state_export_report_path",
            "state_restore_restored",
            "state_restore_snapshot_path",
            "state_restore_audit_overall_status",
            "state_restore_phase_gate_decision",
            "state_restore_report_path",
        )
    }
    remediation_fields = {
        key: value
        for source in (
            operations_dashboard,
            operations_bundle,
            audit_dashboard,
            audit_bundle,
        )
        if isinstance(source, dict)
        for key, value in source.items()
        if isinstance(key, str) and key.startswith("timeline_latest_remediation_")
    }
    backtest_metrics_summary = safe_read_json_dict(backtest_metrics_summary_path)
    live_evidence_summary = safe_read_json_dict(live_evidence_summary_path)
    restart_pointers = {
        "current_state_index_report": str(out_path) if out_path is not None else None,
        "readiness_snapshot_report": _report_path_for_summary(
            operations_dashboard_summary_path,
            "readiness_snapshot.md",
        ),
        "remediation_planner_summary": (
            str(operations_dashboard_summary_path.parent / "remediation_planner_summary.json")
            if operations_dashboard_summary_path is not None
            else None
        ),
        "remediation_planner_report": _report_path_for_summary(
            operations_dashboard_summary_path,
            "remediation_planner.md",
        ),
        "remediation_execution_plan_summary": (
            str(operations_dashboard_summary_path.parent / "remediation_execution_plan_summary.json")
            if operations_dashboard_summary_path is not None
            else None
        ),
        "remediation_execution_plan_report": _report_path_for_summary(
            operations_dashboard_summary_path,
            "remediation_execution_plan.md",
        ),
        "remediation_session_summary": (
            str(operations_dashboard_summary_path.parent / "remediation_session_summary.json")
            if operations_dashboard_summary_path is not None
            else None
        ),
        "remediation_session_report": _report_path_for_summary(
            operations_dashboard_summary_path,
            "remediation_session.md",
        ),
        "remediation_session_checkpoint_summary": (
            str(
                operations_dashboard_summary_path.parent
                / "remediation_session_checkpoint_summary.json"
            )
            if operations_dashboard_summary_path is not None
            else None
        ),
        "remediation_session_checkpoint_report": _report_path_for_summary(
            operations_dashboard_summary_path,
            "remediation_session_checkpoint.md",
        ),
        "remediation_scoreboard_summary": (
            str(operations_dashboard_summary_path.parent / "remediation_scoreboard_summary.json")
            if operations_dashboard_summary_path is not None
            else None
        ),
        "remediation_scoreboard_report": _report_path_for_summary(
            operations_dashboard_summary_path,
            "remediation_scoreboard.md",
        ),
        "remediation_evaluator_summary": (
            str(operations_dashboard_summary_path.parent / "remediation_evaluator_summary.json")
            if operations_dashboard_summary_path is not None
            else None
        ),
        "remediation_evaluator_report": _report_path_for_summary(
            operations_dashboard_summary_path,
            "remediation_evaluator.md",
        ),
        "remediation_evidence_summary": (
            str(operations_dashboard_summary_path.parent / "remediation_evidence_summary.json")
            if operations_dashboard_summary_path is not None
            else None
        ),
        "remediation_evidence_report": _report_path_for_summary(
            operations_dashboard_summary_path,
            "remediation_evidence.md",
        ),
        "remediation_command_results_summary": (
            str(
                operations_dashboard_summary_path.parent
                / "remediation_command_results_summary.json"
            )
            if operations_dashboard_summary_path is not None
            else None
        ),
        "remediation_command_results_report": _report_path_for_summary(
            operations_dashboard_summary_path,
            "remediation_command_results.md",
        ),
        "execution_balance_status_report": _report_path_for_summary(
            operations_dashboard_summary_path,
            "execution_balance_status.md",
        ),
        "execution_fill_status_report": _report_path_for_summary(
            operations_dashboard_summary_path,
            "execution_fill_status.md",
        ),
        "execution_order_status_report": _report_path_for_summary(
            operations_dashboard_summary_path,
            "execution_order_status.md",
        ),
        "execution_cancel_order_report": _report_path_for_summary(
            operations_dashboard_summary_path,
            "execution_cancel_order.md",
        ),
        "execution_close_position_report": _report_path_for_summary(
            operations_dashboard_summary_path,
            "execution_close_position.md",
        ),
        "execution_reconcile_positions_report": _report_path_for_summary(
            operations_dashboard_summary_path,
            "execution_reconcile_positions.md",
        ),
        "daemon_manifest_report": _report_path_for_summary(
            operations_dashboard_summary_path,
            "daemon_manifest.md",
        ),
        "state_export_report": _report_path_for_summary(
            operations_dashboard_summary_path,
            "state_export.md",
        ),
        "state_restore_report": _report_path_for_summary(
            operations_dashboard_summary_path,
            "state_restore.md",
        ),
        "live_evidence_report": _live_evidence_report_path(
            live_evidence_summary_path,
            live_evidence_summary,
        ),
    }

    summary = {
        "overall_status": operations_dashboard.get("overall_status") or operations_bundle.get("overall_status"),
        "phase_gate_summary": phase_gate,
        "audit_summary": audit_summary,
        **latest_execution_lineage,
        **execution_adapter_fields,
        **remediation_fields,
        **phase_gate_fields,
        **audit_dashboard_fields,
        **audit_timeline_fields,
        **audit_bundle_history_fields,
        "operations_cycle_count": operations_bundle.get("cycle_count"),
        "execution_summary": execution_snapshot,
        "execution_comparison_summary": execution_comparison,
        "execution_diagnostics_summary": execution_diagnostics,
        "execution_gap_history_summary": execution_gap_history,
        "execution_state_comparison_summary": execution_state_comparison_history,
        "execution_snapshot_drift_summary": execution_snapshot_drift_history,
        "execution_drift_overview_summary": execution_drift_overview,
        **execution_snapshot_fields,
        **execution_comparison_fields,
        **execution_diagnostics_fields,
        "execution_comparison_ready": execution_comparison_fields.get(
            "execution_comparison_all_registries_present"
        ),
        **execution_gap_history_fields,
        **execution_state_comparison_fields,
        **execution_snapshot_drift_fields,
        **execution_drift_fields,
        "backtest_total_trade_count": backtest_metrics_summary.get("total_trade_count"),
        "backtest_symbols": backtest_metrics_summary.get("symbols", []),
        "live_evidence_status": live_evidence_summary.get("status"),
        "live_evidence_decision": live_evidence_summary.get("decision"),
        "live_evidence_run_id": live_evidence_summary.get("run_id"),
        "live_evidence_report_path": restart_pointers.get("live_evidence_report"),
        "research_quality_report_exists": bool(research_quality_report_path and research_quality_report_path.exists()),
        "quick_navigation": _quick_navigation(
            restart_pointers,
            phase_gate_fields.get("phase_gate_review_report_path"),
        ),
        "restart_pointers": restart_pointers,
        "related_reports": _related_reports(
            restart_pointers,
            phase_gate_fields.get("phase_gate_review_report_path"),
        ),
        "artifacts": {
            "operations_dashboard_summary": str(operations_dashboard_summary_path) if operations_dashboard_summary_path else None,
            "operations_bundle_manifest": str(operations_bundle_manifest_path) if operations_bundle_manifest_path else None,
            "audit_dashboard_summary": str(audit_dashboard_summary_path) if audit_dashboard_summary_path else None,
            "audit_bundle_manifest": str(audit_bundle_manifest_path) if audit_bundle_manifest_path else None,
            "phase_gate_summary": str(phase_gate_summary_path) if phase_gate_summary_path else None,
            "execution_snapshot_summary": str(execution_snapshot_summary_path) if execution_snapshot_summary_path else None,
            "execution_venue_comparison_summary": (
                str(execution_venue_comparison_summary_path)
                if execution_venue_comparison_summary_path
                else None
            ),
            "execution_venue_diagnostics_summary": (
                str(execution_venue_diagnostics_summary_path)
                if execution_venue_diagnostics_summary_path
                else None
            ),
            "execution_gap_history_summary": (
                str(execution_gap_history_summary_path) if execution_gap_history_summary_path else None
            ),
            "execution_state_comparison_history_summary": (
                str(execution_state_comparison_history_summary_path)
                if execution_state_comparison_history_summary_path
                else None
            ),
            "execution_snapshot_drift_history_summary": (
                str(execution_snapshot_drift_history_summary_path)
                if execution_snapshot_drift_history_summary_path
                else None
            ),
            "execution_drift_overview_summary": (
                str(execution_drift_overview_summary_path) if execution_drift_overview_summary_path else None
            ),
            "backtest_metrics_summary": str(backtest_metrics_summary_path) if backtest_metrics_summary_path else None,
            "live_evidence_summary": str(live_evidence_summary_path) if live_evidence_summary_path else None,
            "live_evidence_report": restart_pointers.get("live_evidence_report"),
            "research_quality_report": str(research_quality_report_path) if research_quality_report_path else None,
            **restart_pointers,
        },
        "recommended_read_order": recommended_read_order(
            [
            "data/ops/current_state_index.json",
            "data/reports/current_state_index.md",
            "data/reports/readiness_snapshot.md",
            "data/reports/remediation_scoreboard.md",
            "data/reports/remediation_session_checkpoint.md",
            "data/reports/remediation_session.md",
            "data/reports/remediation_execution_plan.md",
            "data/reports/remediation_planner.md",
            "data/ops/phase_gate_review_summary.json",
            "data/ops/execution_snapshot_summary.json",
            "data/ops/execution_venue_comparison_summary.json",
            "data/ops/execution_venue_diagnostics_summary.json",
            "data/ops/execution_gap_history_summary.json",
            "data/ops/execution_state_comparison_history_summary.json",
            "data/ops/execution_snapshot_drift_history_summary.json",
            "data/ops/execution_drift_overview_summary.json",
            "data/reports/execution_balance_status.md",
            "data/reports/execution_fill_status.md",
            "data/reports/execution_order_status.md",
            "data/reports/execution_cancel_order.md",
            "data/reports/execution_close_position.md",
            "data/reports/execution_reconcile_positions.md",
            "data/reports/daemon_manifest.md",
            "data/reports/state_export.md",
            "data/reports/state_restore.md",
            "data/ops/operations_dashboard_summary.json",
            "data/ops/audit_dashboard_summary.json",
            "data/ops/operations_bundle_manifest.json",
            "data/ops/audit_bundle_manifest.json",
            "docs/live_evidence_reports/live_evidence_report_<run_id>.md",
            "data/research/backtest_metrics_summary.json",
            ]
        ),
    }

    lines = [
        "# Current State Index",
        "",
        "## Overview",
        "",
        f"- overall_status: {summary['overall_status']}",
        f"- phase_gate_decision: {summary['phase_gate_decision']}",
        f"- phase2_entry_allowed: {summary['phase2_entry_allowed']}",
        f"- phase_gate_reason: {summary['phase_gate_reason']}",
        f"- phase_gate_strict_validation_passed: {summary['phase_gate_strict_validation_passed']}",
        f"- phase_gate_strict_validation_issue_count: {summary['phase_gate_strict_validation_issue_count']}",
        f"- phase_gate_checked_files: {summary['phase_gate_checked_files']}",
        f"- phase_gate_review_report_path: {summary['phase_gate_review_report_path']}",
        f"- audit_overall_status: {summary['audit_overall_status']}",
        f"- audit_latest_operation: {summary['audit_latest_operation']}",
        *latest_execution_lineage_flat_lines(summary),
        f"- timeline_latest_remediation_planner_status: {summary.get('timeline_latest_remediation_planner_status')}",
        f"- timeline_latest_remediation_planner_next_best_command: {summary.get('timeline_latest_remediation_planner_next_best_command')}",
        (
            "- timeline_latest_remediation_planner_feedback_priority_reason: "
            f"{summary.get('timeline_latest_remediation_planner_feedback_priority_reason')}"
        ),
        f"- timeline_latest_remediation_execution_plan_status: {summary.get('timeline_latest_remediation_execution_plan_status')}",
        f"- timeline_latest_remediation_execution_plan_next_action_command: {summary.get('timeline_latest_remediation_execution_plan_next_action_command')}",
        (
            "- timeline_latest_remediation_execution_plan_feedback_priority_reason: "
            f"{summary.get('timeline_latest_remediation_execution_plan_feedback_priority_reason')}"
        ),
        f"- timeline_latest_remediation_session_status: {summary.get('timeline_latest_remediation_session_status')}",
        f"- timeline_latest_remediation_session_next_pending_command: {summary.get('timeline_latest_remediation_session_next_pending_command')}",
        (
            "- timeline_latest_remediation_session_feedback_priority_reason: "
            f"{summary.get('timeline_latest_remediation_session_feedback_priority_reason')}"
        ),
        f"- timeline_latest_remediation_checkpoint_status: {summary.get('timeline_latest_remediation_checkpoint_status')}",
        f"- timeline_latest_remediation_checkpoint_next_action_command: {summary.get('timeline_latest_remediation_checkpoint_next_action_command')}",
        (
            "- timeline_latest_remediation_checkpoint_feedback_priority_reason: "
            f"{summary.get('timeline_latest_remediation_checkpoint_feedback_priority_reason')}"
        ),
        f"- timeline_latest_remediation_scoreboard_status: {summary.get('timeline_latest_remediation_scoreboard_status')}",
        f"- timeline_latest_remediation_scoreboard_next_action_command: {summary.get('timeline_latest_remediation_scoreboard_next_action_command')}",
        (
            "- timeline_latest_remediation_scoreboard_feedback_priority_reason: "
            f"{summary.get('timeline_latest_remediation_scoreboard_feedback_priority_reason')}"
        ),
        "",
        "## Strict Validation Preview",
        "",
    ]
    validation_issue_previews = phase_gate_issue_preview_lines(summary)
    if validation_issue_previews:
        lines.extend(f"- {item}" for item in validation_issue_previews)
    else:
        lines.append("- issues: none")
    lines.extend(["", "## Research And Backtest", ""])
    lines.extend(
        [
            f"- execution_overall_status: {summary['execution_overall_status']}",
            f"- execution_venue_count: {summary['execution_venue_count']}",
            f"- execution_comparison_ready: {summary['execution_comparison_ready']}",
            f"- execution_diagnostics_status: {summary['execution_diagnostics_status']}",
            f"- execution_balance_gap_detected: {summary['execution_balance_gap_detected']}",
            f"- execution_fills_gap_detected: {summary['execution_fills_gap_detected']}",
            f"- execution_gap_history_entry_count: {summary['execution_gap_history_entry_count']}",
            f"- execution_gap_history_latest_status: {summary['execution_gap_history_latest_status']}",
            f"- execution_gap_history_latest_diagnostics_status: {summary['execution_gap_history_latest_diagnostics_status']}",
            f"- execution_state_comparison_entry_count: {summary['execution_state_comparison_entry_count']}",
            (
                "- execution_state_comparison_latest_status_match: "
                f"{summary['execution_state_comparison_latest_status_match']}"
            ),
            (
                "- execution_state_comparison_mismatching_count: "
                f"{summary['execution_state_comparison_mismatching_count']}"
            ),
            f"- execution_snapshot_drift_entry_count: {summary['execution_snapshot_drift_entry_count']}",
            (
                "- execution_snapshot_drift_latest_status_match: "
                f"{summary['execution_snapshot_drift_latest_status_match']}"
            ),
            (
                "- execution_snapshot_drift_mismatching_snapshot_count: "
                f"{summary['execution_snapshot_drift_mismatching_snapshot_count']}"
            ),
            f"- execution_drift_overview_status: {summary['execution_drift_overview_status']}",
            (
                "- execution_drift_overview_diagnostics_alignment_match: "
                f"{summary['execution_drift_overview_diagnostics_alignment_match']}"
            ),
            (
                "- execution_drift_overview_state_comparison_mismatching_count: "
                f"{summary['execution_drift_overview_state_comparison_mismatching_count']}"
            ),
            (
                "- execution_drift_overview_snapshot_drift_mismatching_snapshot_count: "
                f"{summary['execution_drift_overview_snapshot_drift_mismatching_snapshot_count']}"
            ),
            f"- backtest_total_trade_count: {summary['backtest_total_trade_count']}",
            f"- backtest_symbols: {summary['backtest_symbols']}",
            f"- research_quality_report_exists: {summary['research_quality_report_exists']}",
        ]
    )
    lines.extend(["", "## Execution Adapter Surfaces", ""])
    lines.extend(
        [
            f"- execution_balance_status_venue: {summary.get('execution_balance_status_venue')}",
            f"- execution_balance_status_currency: {summary.get('execution_balance_status_currency')}",
            f"- execution_balance_status_equity: {summary.get('execution_balance_status_equity')}",
            f"- execution_balance_status_available_cash: {summary.get('execution_balance_status_available_cash')}",
            f"- execution_balance_status_margin_used: {summary.get('execution_balance_status_margin_used')}",
            f"- execution_balance_status_notional_usd: {summary.get('execution_balance_status_notional_usd')}",
            f"- execution_balance_status_unrealized_pnl: {summary.get('execution_balance_status_unrealized_pnl')}",
            f"- execution_balance_status_cumulative_rollover_usd: {summary.get('execution_balance_status_cumulative_rollover_usd')}",
            f"- execution_fill_status_venue: {summary.get('execution_fill_status_venue')}",
            f"- execution_fill_status_fills_count: {summary.get('execution_fill_status_fills_count')}",
            f"- execution_fill_status_latest_fill_id: {summary.get('execution_fill_status_latest_fill_id')}",
            f"- execution_fill_status_latest_fill_order_id: {summary.get('execution_fill_status_latest_fill_order_id')}",
            f"- execution_fill_status_latest_fill_symbol: {summary.get('execution_fill_status_latest_fill_symbol')}",
            f"- execution_fill_status_latest_fill_side: {summary.get('execution_fill_status_latest_fill_side')}",
            f"- execution_fill_status_latest_fill_quantity: {summary.get('execution_fill_status_latest_fill_quantity')}",
            f"- execution_fill_status_latest_fill_price: {summary.get('execution_fill_status_latest_fill_price')}",
            f"- execution_fill_status_latest_fill_status: {summary.get('execution_fill_status_latest_fill_status')}",
            f"- execution_fill_status_latest_fill_ts_fill: {summary.get('execution_fill_status_latest_fill_ts_fill')}",
            f"- execution_order_status_venue: {summary.get('execution_order_status_venue')}",
            f"- execution_order_status_order_id: {summary.get('execution_order_status_order_id')}",
            f"- execution_order_status_status: {summary.get('execution_order_status_status')}",
            f"- execution_order_status_symbol: {summary.get('execution_order_status_symbol')}",
            f"- execution_order_status_side: {summary.get('execution_order_status_side')}",
            f"- execution_order_status_quantity: {summary.get('execution_order_status_quantity')}",
            f"- execution_cancel_order_target: {summary.get('execution_cancel_order_target')}",
            f"- execution_cancel_order_status: {summary.get('execution_cancel_order_status')}",
            f"- execution_close_position_target: {summary.get('execution_close_position_target')}",
            f"- execution_close_position_status: {summary.get('execution_close_position_status')}",
            f"- execution_reconcile_positions_matched: {summary.get('execution_reconcile_positions_matched')}",
            (
                "- execution_reconcile_positions_missing_in_adapter_count: "
                f"{summary.get('execution_reconcile_positions_missing_in_adapter_count')}"
            ),
            (
                "- execution_reconcile_positions_missing_in_internal_count: "
                f"{summary.get('execution_reconcile_positions_missing_in_internal_count')}"
            ),
            f"- execution_read_only_surfaces_venue_count: {summary.get('execution_read_only_surfaces_venue_count')}",
            (
                "- execution_read_only_surfaces_with_balance_snapshot_count: "
                f"{summary.get('execution_read_only_surfaces_with_balance_snapshot_count')}"
            ),
            (
                "- execution_read_only_surfaces_with_positions_snapshot_count: "
                f"{summary.get('execution_read_only_surfaces_with_positions_snapshot_count')}"
            ),
            (
                "- execution_read_only_surfaces_with_fills_snapshot_count: "
                f"{summary.get('execution_read_only_surfaces_with_fills_snapshot_count')}"
            ),
            (
                "- execution_read_only_surfaces_with_order_status_snapshot_count: "
                f"{summary.get('execution_read_only_surfaces_with_order_status_snapshot_count')}"
            ),
            (
                "- execution_read_only_surfaces_reconciled_venue_count: "
                f"{summary.get('execution_read_only_surfaces_reconciled_venue_count')}"
            ),
            (
                "- execution_read_only_surfaces_with_positions_financial_totals_count: "
                f"{summary.get('execution_read_only_surfaces_with_positions_financial_totals_count')}"
            ),
            (
                "- execution_read_only_surfaces_with_positions_rollover_metrics_count: "
                f"{summary.get('execution_read_only_surfaces_with_positions_rollover_metrics_count')}"
            ),
            (
                "- execution_read_only_surfaces_with_positions_protection_metrics_count: "
                f"{summary.get('execution_read_only_surfaces_with_positions_protection_metrics_count')}"
            ),
            (
                "- execution_read_only_surfaces_with_positions_leverage_metrics_count: "
                f"{summary.get('execution_read_only_surfaces_with_positions_leverage_metrics_count')}"
            ),
            (
                "- execution_read_only_surfaces_with_positions_return_metrics_count: "
                f"{summary.get('execution_read_only_surfaces_with_positions_return_metrics_count')}"
            ),
            (
                "- execution_read_only_surfaces_with_positions_day_trade_metrics_count: "
                f"{summary.get('execution_read_only_surfaces_with_positions_day_trade_metrics_count')}"
            ),
            (
                "- execution_read_only_surfaces_with_positions_limit_metrics_count: "
                f"{summary.get('execution_read_only_surfaces_with_positions_limit_metrics_count')}"
            ),
            (
                "- execution_read_only_surfaces_with_positions_quantity_metrics_count: "
                f"{summary.get('execution_read_only_surfaces_with_positions_quantity_metrics_count')}"
            ),
            (
                "- execution_read_only_surfaces_positions_notional_usd_total: "
                f"{summary.get('execution_read_only_surfaces_positions_notional_usd_total')}"
            ),
            (
                "- execution_read_only_surfaces_positions_unrealized_pnl_usd_total: "
                f"{summary.get('execution_read_only_surfaces_positions_unrealized_pnl_usd_total')}"
            ),
            (
                "- execution_read_only_surfaces_positions_collateral_used_usd_total: "
                f"{summary.get('execution_read_only_surfaces_positions_collateral_used_usd_total')}"
            ),
            (
                "- execution_read_only_surfaces_positions_max_withdrawable_usd_total: "
                f"{summary.get('execution_read_only_surfaces_positions_max_withdrawable_usd_total')}"
            ),
            (
                "- execution_read_only_surfaces_positions_cumulative_rollover_usd_total: "
                f"{summary.get('execution_read_only_surfaces_positions_cumulative_rollover_usd_total')}"
            ),
            (
                "- execution_read_only_surfaces_positions_with_liquidation_price_count: "
                f"{summary.get('execution_read_only_surfaces_positions_with_liquidation_price_count')}"
            ),
            (
                "- execution_read_only_surfaces_positions_with_take_profit_count: "
                f"{summary.get('execution_read_only_surfaces_positions_with_take_profit_count')}"
            ),
            (
                "- execution_read_only_surfaces_positions_with_stop_loss_count: "
                f"{summary.get('execution_read_only_surfaces_positions_with_stop_loss_count')}"
            ),
            (
                "- execution_read_only_surfaces_positions_day_trade_count: "
                f"{summary.get('execution_read_only_surfaces_positions_day_trade_count')}"
            ),
            (
                "- execution_read_only_surfaces_positions_average_leverage: "
                f"{summary.get('execution_read_only_surfaces_positions_average_leverage')}"
            ),
            (
                "- execution_read_only_surfaces_positions_average_return_on_equity: "
                f"{summary.get('execution_read_only_surfaces_positions_average_return_on_equity')}"
            ),
            (
                "- execution_read_only_surfaces_positions_max_leverage: "
                f"{summary.get('execution_read_only_surfaces_positions_max_leverage')}"
            ),
            (
                "- execution_read_only_surfaces_positions_total_quantity: "
                f"{summary.get('execution_read_only_surfaces_positions_total_quantity')}"
            ),
            (
                "- execution_read_only_surfaces_positions_total_realized_pnl: "
                f"{summary.get('execution_read_only_surfaces_positions_total_realized_pnl')}"
            ),
            (
                "- execution_read_only_surfaces_latest_positions_server_time_ms: "
                f"{summary.get('execution_read_only_surfaces_latest_positions_server_time_ms')}"
            ),
            (
                "- execution_read_only_surfaces_latest_positions_open_timestamp_ms: "
                f"{summary.get('execution_read_only_surfaces_latest_positions_open_timestamp_ms')}"
            ),
            (
                "- execution_read_only_surfaces_latest_positions_updated_at: "
                f"{summary.get('execution_read_only_surfaces_latest_positions_updated_at')}"
            ),
            (
                "- execution_read_only_surfaces_latest_positions_client_ts: "
                f"{summary.get('execution_read_only_surfaces_latest_positions_client_ts')}"
            ),
            f"- execution_read_only_surfaces_report_path: {summary.get('execution_read_only_surfaces_report_path')}",
        ]
    )
    lines.extend(["", "## State And Daemon Surfaces", ""])
    lines.extend(
        [
            f"- daemon_manifest_mode: {summary.get('daemon_manifest_mode')}",
            f"- daemon_manifest_command: {summary.get('daemon_manifest_command')}",
            f"- daemon_manifest_state_store_path: {summary.get('daemon_manifest_state_store_path')}",
            f"- state_export_snapshot_path: {summary.get('state_export_snapshot_path')}",
            f"- state_export_audit_overall_status: {summary.get('state_export_audit_overall_status')}",
            f"- state_export_phase_gate_decision: {summary.get('state_export_phase_gate_decision')}",
            (
                "- state_export_readiness_next_phase_candidate: "
                f"{summary.get('state_export_readiness_next_phase_candidate')}"
            ),
            f"- state_restore_restored: {summary.get('state_restore_restored')}",
            f"- state_restore_snapshot_path: {summary.get('state_restore_snapshot_path')}",
            f"- state_restore_audit_overall_status: {summary.get('state_restore_audit_overall_status')}",
            f"- state_restore_phase_gate_decision: {summary.get('state_restore_phase_gate_decision')}",
        ]
    )
    lines.extend(["", "## Live Evidence", ""])
    lines.extend(
        [
            f"- live_evidence_status: {summary['live_evidence_status']}",
            f"- live_evidence_decision: {summary['live_evidence_decision']}",
            f"- live_evidence_run_id: {summary['live_evidence_run_id']}",
            f"- live_evidence_report_path: {summary['live_evidence_report_path']}",
        ]
    )
    lines.extend(["", "## Operations", ""])
    lines.append(f"- operations_cycle_count: {summary['operations_cycle_count']}")
    lines.extend(["", "## Quick Navigation", ""])
    for key, value in summary["quick_navigation"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Related Reports", ""])
    for key, value in summary["related_reports"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Restart Pointers", ""])
    for key, value in summary["restart_pointers"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Artifact Paths", ""])
    for key, value in summary["artifacts"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Recommended Read Order", ""])
    lines.extend(f"- {item}" for item in summary["recommended_read_order"])
    lines.append("")

    text = "\n".join(lines)
    if out_path is not None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text, encoding="utf-8")
    if summary_path is not None:
        write_json(summary_path, summary)
    return text
