from __future__ import annotations

from pathlib import Path

from sis.reports.loaders import normalized_summary, safe_read_json_dict
from sis.reports.summary_normalizers import (
    execution_comparison_flat_fields,
    execution_diagnostics_flat_fields,
    execution_gap_history_flat_fields,
    execution_snapshot_drift_flat_fields,
    execution_snapshot_flat_fields,
    execution_state_comparison_flat_fields,
    execution_drift_overview_flat_fields,
    latest_execution_lineage_flat_lines,
    normalize_execution_comparison_summary,
    normalize_execution_diagnostics_summary,
    normalize_execution_gap_history_summary,
    normalize_execution_snapshot_drift_summary,
    normalize_execution_snapshot_summary,
    normalize_execution_state_comparison_summary,
    normalize_execution_drift_overview_summary,
    normalize_phase_gate_summary,
    latest_execution_lineage_fields_from_summary,
    phase_gate_flat_fields,
    phase_gate_issue_preview_lines,
)
from sis.storage.jsonl_store import write_json


def _remediation_fields_from_sources(
    current_state: dict[str, object],
    operations: dict[str, object],
) -> dict[str, object]:
    keys = (
        "timeline_latest_remediation_planner_status",
        "timeline_latest_remediation_planner_next_best_command",
        "timeline_latest_remediation_planner_feedback_priority_reason",
        "timeline_latest_remediation_execution_plan_status",
        "timeline_latest_remediation_execution_plan_next_action_command",
        "timeline_latest_remediation_execution_plan_feedback_priority_reason",
        "timeline_latest_remediation_session_status",
        "timeline_latest_remediation_session_next_pending_command",
        "timeline_latest_remediation_session_feedback_priority_reason",
        "timeline_latest_remediation_checkpoint_status",
        "timeline_latest_remediation_checkpoint_next_action_command",
        "timeline_latest_remediation_checkpoint_feedback_priority_reason",
        "timeline_latest_remediation_scoreboard_status",
        "timeline_latest_remediation_scoreboard_next_action_command",
        "timeline_latest_remediation_scoreboard_feedback_priority_reason",
    )
    merged: dict[str, object] = {}
    for key in keys:
        if current_state.get(key) is not None:
            merged[key] = current_state.get(key)
        elif operations.get(key) is not None:
            merged[key] = operations.get(key)
    return merged


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
        ("readiness_snapshot_report", restart_pointers.get("readiness_snapshot_report")),
        ("current_state_index_report", restart_pointers.get("current_state_index_report")),
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
        ("readiness_snapshot_report", restart_pointers.get("readiness_snapshot_report")),
        ("current_state_index_report", restart_pointers.get("current_state_index_report")),
        ("phase_gate_review_report", phase_gate_review_report_path),
        ("remediation_scoreboard_report", restart_pointers.get("remediation_scoreboard_report")),
        ("live_evidence_report", restart_pointers.get("live_evidence_report")),
    )
    return {
        key: value
        for key, value in items
        if isinstance(value, str) and value
    }


def build_readiness_snapshot(
    *,
    current_state_index_path: Path | None = None,
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
    operations_dashboard_summary_path: Path | None = None,
    out_path: Path | None = None,
    summary_path: Path | None = None,
) -> str:
    current_state = safe_read_json_dict(current_state_index_path)
    phase_gate = normalized_summary(phase_gate_summary_path, normalize_phase_gate_summary)
    execution = normalized_summary(
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
    phase_gate_fields = phase_gate_flat_fields(phase_gate)
    execution_snapshot_fields = execution_snapshot_flat_fields(execution)
    execution_comparison_fields = execution_comparison_flat_fields(execution_comparison)
    execution_diagnostics_fields = execution_diagnostics_flat_fields(execution_diagnostics)
    execution_gap_history_fields = execution_gap_history_flat_fields(execution_gap_history)
    execution_state_comparison_fields = execution_state_comparison_flat_fields(
        execution_state_comparison_history
    )
    execution_snapshot_drift_fields = execution_snapshot_drift_flat_fields(
        execution_snapshot_drift_history
    )
    execution_drift_fields = execution_drift_overview_flat_fields(execution_drift_overview)
    latest_execution_lineage = latest_execution_lineage_fields_from_summary(current_state)
    backtest = safe_read_json_dict(backtest_metrics_summary_path)
    live_evidence = safe_read_json_dict(live_evidence_summary_path)
    operations = safe_read_json_dict(operations_dashboard_summary_path)
    execution_adapter_fields = {
        key: operations.get(key)
        for key in (
            "execution_balance_status_venue",
            "execution_balance_status_currency",
            "execution_balance_status_equity",
            "execution_balance_status_available_cash",
            "execution_balance_status_snapshot_exists",
            "execution_balance_status_report_path",
            "execution_fill_status_venue",
            "execution_fill_status_fills_count",
            "execution_fill_status_latest_fill_id",
            "execution_fill_status_latest_fill_status",
            "execution_fill_status_report_path",
            "execution_order_status_venue",
            "execution_order_status_order_id",
            "execution_order_status_status",
            "execution_order_status_symbol",
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
    remediation_fields = _remediation_fields_from_sources(current_state, operations)
    restart_pointers = {
        "readiness_snapshot_report": str(out_path) if out_path is not None else None,
        "current_state_index_report": _report_path_for_summary(
            current_state_index_path,
            "current_state_index.md",
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
            live_evidence,
        ),
    }

    phase2_entry_allowed = bool(phase_gate_fields.get("phase2_entry_allowed"))
    execution_ready = (
        execution_snapshot_fields.get("execution_overall_status") == "ok"
        and int(execution_snapshot_fields.get("execution_venue_count") or 0) > 0
        and execution_comparison_fields.get("execution_comparison_all_registries_present") is True
        and execution_diagnostics_fields.get("execution_diagnostics_status") == "ok"
        and int(execution_gap_history_fields.get("execution_gap_history_entry_count") or 0) > 0
        and int(
            execution_state_comparison_fields.get("execution_state_comparison_mismatching_count") or 0
        )
        == 0
        and int(
            execution_snapshot_drift_fields.get(
                "execution_snapshot_drift_mismatching_snapshot_count"
            )
            or 0
        )
        == 0
        and execution_drift_fields.get("execution_drift_overview_status") == "ok"
    )
    backtest_ready = int(backtest.get("total_trade_count") or 0) > 0
    live_evidence_ready = live_evidence.get("decision") in {"GO", "CONDITIONAL_GO_NEEDS_SIGNAL_BACKTEST"}
    operations_ready = operations.get("overall_status") == "ok"

    summary = {
        "overall_status": current_state.get("overall_status") or operations.get("overall_status"),
        "phase_gate_decision": phase_gate_fields.get("phase_gate_decision"),
        "phase2_entry_allowed": phase2_entry_allowed,
        "phase2_entry_reason": phase_gate_fields.get("phase2_entry_reason"),
        "phase_gate_reason": phase_gate_fields.get("phase_gate_reason"),
        "phase_gate_strict_validation_passed": phase_gate_fields.get("phase_gate_strict_validation_passed"),
        "phase_gate_strict_validation_issue_count": phase_gate_fields.get(
            "phase_gate_strict_validation_issue_count"
        ),
        "phase_gate_checked_files": phase_gate_fields.get("phase_gate_checked_files"),
        "phase_gate_review_report_path": phase_gate_fields.get("phase_gate_review_report_path"),
        "phase_gate_strict_validation_issues": phase_gate_fields.get(
            "phase_gate_strict_validation_issues"
        ),
        "phase_gate_summary": phase_gate,
        **latest_execution_lineage,
        "execution_summary": execution,
        "execution_comparison_summary": execution_comparison,
        "execution_diagnostics_summary": execution_diagnostics,
        "execution_gap_history_summary": execution_gap_history,
        "execution_state_comparison_summary": execution_state_comparison_history,
        "execution_snapshot_drift_summary": execution_snapshot_drift_history,
        "execution_drift_overview_summary": execution_drift_overview,
        "execution_ready": execution_ready,
        **execution_snapshot_fields,
        **execution_comparison_fields,
        **execution_diagnostics_fields,
        **execution_gap_history_fields,
        **execution_state_comparison_fields,
        **execution_snapshot_drift_fields,
        **execution_drift_fields,
        "backtest_ready": backtest_ready,
        "backtest_total_trade_count": backtest.get("total_trade_count"),
        "live_evidence_ready": live_evidence_ready,
        "live_evidence_status": live_evidence.get("status"),
        "live_evidence_decision": live_evidence.get("decision"),
        "live_evidence_report_path": restart_pointers.get("live_evidence_report"),
        "operations_ready": operations_ready,
        "operations_overall_status": operations.get("overall_status"),
        "research_quality_report_exists": current_state.get("research_quality_report_exists"),
        "next_phase_candidate": "Phase 2" if phase2_entry_allowed else "Stay Phase 1",
        "readiness_next_phase_candidate": "Phase 2" if phase2_entry_allowed else "Stay Phase 1",
        "readiness_execution_ready": execution_ready,
        **execution_adapter_fields,
        **remediation_fields,
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
            "current_state_index": str(current_state_index_path) if current_state_index_path else None,
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
            "operations_dashboard_summary": str(operations_dashboard_summary_path) if operations_dashboard_summary_path else None,
            "live_evidence_report": restart_pointers.get("live_evidence_report"),
            **restart_pointers,
        },
        "recommended_read_order": [
            "docs/ACCEPTANCE_AUDIT.md",
            "docs/IMPLEMENTATION_STATUS.md",
            "data/ops/readiness_snapshot.json",
            "data/reports/readiness_snapshot.md",
            "data/ops/current_state_index.json",
            "data/reports/current_state_index.md",
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
            "docs/live_evidence_reports/live_evidence_report_<run_id>.md",
            "data/research/backtest_metrics_summary.json",
        ],
    }

    lines = [
        "# Readiness Snapshot",
        "",
        "## Overall",
        "",
        f"- overall_status: {summary['overall_status']}",
        f"- next_phase_candidate: {summary['next_phase_candidate']}",
        "",
        "## Phase Gate",
        "",
        f"- phase_gate_decision: {summary['phase_gate_decision']}",
        f"- phase2_entry_allowed: {summary['phase2_entry_allowed']}",
        f"- phase2_entry_reason: {summary['phase2_entry_reason']}",
        f"- phase_gate_reason: {summary['phase_gate_reason']}",
        f"- phase_gate_strict_validation_passed: {summary['phase_gate_strict_validation_passed']}",
        f"- phase_gate_strict_validation_issue_count: {summary['phase_gate_strict_validation_issue_count']}",
        f"- phase_gate_checked_files: {summary['phase_gate_checked_files']}",
        f"- phase_gate_review_report_path: {summary['phase_gate_review_report_path']}",
        "",
        "## Strict Validation Preview",
        "",
    ]
    validation_issue_previews = phase_gate_issue_preview_lines(summary)
    if validation_issue_previews:
        lines.extend(f"- {item}" for item in validation_issue_previews)
    else:
        lines.append("- issues: none")
    lines.extend(["", "## Readiness Flags", ""])
    lines.extend(
        [
            f"- execution_ready: {summary['execution_ready']}",
            f"- backtest_ready: {summary['backtest_ready']}",
            f"- live_evidence_ready: {summary['live_evidence_ready']}",
            f"- operations_ready: {summary['operations_ready']}",
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
            f"- execution_fill_status_fills_count: {summary.get('execution_fill_status_fills_count')}",
            f"- execution_fill_status_latest_fill_id: {summary.get('execution_fill_status_latest_fill_id')}",
            f"- execution_fill_status_latest_fill_status: {summary.get('execution_fill_status_latest_fill_status')}",
            f"- execution_order_status_order_id: {summary.get('execution_order_status_order_id')}",
            f"- execution_order_status_status: {summary.get('execution_order_status_status')}",
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
    lines.extend(["", "## Restart Pointers", ""])
    for key, value in summary["restart_pointers"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Quick Navigation", ""])
    for key, value in summary["quick_navigation"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Related Reports", ""])
    for key, value in summary["related_reports"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Latest Execution Lineage", ""])
    lines.extend(latest_execution_lineage_flat_lines(summary))
    lines.extend(["", "## Current Remediation Queue", ""])
    lines.extend(
        [
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
        ]
    )
    lines.extend(["", "## Current State Metrics", ""])
    lines.extend(
        [
            f"- execution_overall_status: {summary['execution_overall_status']}",
            f"- execution_venue_count: {summary['execution_venue_count']}",
            f"- execution_comparison_all_registries_present: {summary['execution_comparison_all_registries_present']}",
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
            f"- live_evidence_status: {summary['live_evidence_status']}",
            f"- live_evidence_decision: {summary['live_evidence_decision']}",
            f"- live_evidence_report_path: {summary['live_evidence_report_path']}",
            f"- operations_overall_status: {summary['operations_overall_status']}",
        ]
    )
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
