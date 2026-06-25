from __future__ import annotations

from pathlib import Path
from typing import Mapping


REMEDIATION_FIELD_KEYS = (
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


def remediation_fields_from_sources(
    current_state: dict[str, object],
    operations: dict[str, object],
) -> dict[str, object]:
    merged: dict[str, object] = {}
    for key in REMEDIATION_FIELD_KEYS:
        if current_state.get(key) is not None:
            merged[key] = current_state.get(key)
        elif operations.get(key) is not None:
            merged[key] = operations.get(key)
    return merged


def report_path_for_summary(path: Path | None, report_name: str) -> str | None:
    if path is None:
        return None
    base = path.parent.parent if path.parent.name == "ops" else path.parent
    return str(base / "reports" / report_name)


def live_evidence_report_path(
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


def restart_pointers_from_paths(
    *,
    out_path: Path | None,
    current_state_index_path: Path | None,
    operations_dashboard_summary_path: Path | None,
    live_evidence_summary_path: Path | None,
    live_evidence: dict[str, object],
) -> dict[str, str | None]:
    return {
        "readiness_snapshot_report": str(out_path) if out_path is not None else None,
        "current_state_index_report": report_path_for_summary(
            current_state_index_path,
            "current_state_index.md",
        ),
        "remediation_planner_summary": _ops_summary_path(
            operations_dashboard_summary_path,
            "remediation_planner_summary.json",
        ),
        "remediation_planner_report": report_path_for_summary(
            operations_dashboard_summary_path,
            "remediation_planner.md",
        ),
        "remediation_execution_plan_summary": _ops_summary_path(
            operations_dashboard_summary_path,
            "remediation_execution_plan_summary.json",
        ),
        "remediation_execution_plan_report": report_path_for_summary(
            operations_dashboard_summary_path,
            "remediation_execution_plan.md",
        ),
        "remediation_session_summary": _ops_summary_path(
            operations_dashboard_summary_path,
            "remediation_session_summary.json",
        ),
        "remediation_session_report": report_path_for_summary(
            operations_dashboard_summary_path,
            "remediation_session.md",
        ),
        "remediation_session_checkpoint_summary": _ops_summary_path(
            operations_dashboard_summary_path,
            "remediation_session_checkpoint_summary.json",
        ),
        "remediation_session_checkpoint_report": report_path_for_summary(
            operations_dashboard_summary_path,
            "remediation_session_checkpoint.md",
        ),
        "remediation_scoreboard_summary": _ops_summary_path(
            operations_dashboard_summary_path,
            "remediation_scoreboard_summary.json",
        ),
        "remediation_scoreboard_report": report_path_for_summary(
            operations_dashboard_summary_path,
            "remediation_scoreboard.md",
        ),
        "execution_balance_status_report": report_path_for_summary(
            operations_dashboard_summary_path,
            "execution_balance_status.md",
        ),
        "execution_fill_status_report": report_path_for_summary(
            operations_dashboard_summary_path,
            "execution_fill_status.md",
        ),
        "execution_order_status_report": report_path_for_summary(
            operations_dashboard_summary_path,
            "execution_order_status.md",
        ),
        "execution_cancel_order_report": report_path_for_summary(
            operations_dashboard_summary_path,
            "execution_cancel_order.md",
        ),
        "execution_close_position_report": report_path_for_summary(
            operations_dashboard_summary_path,
            "execution_close_position.md",
        ),
        "execution_reconcile_positions_report": report_path_for_summary(
            operations_dashboard_summary_path,
            "execution_reconcile_positions.md",
        ),
        "daemon_manifest_report": report_path_for_summary(
            operations_dashboard_summary_path,
            "daemon_manifest.md",
        ),
        "daemon_loop_report": report_path_for_summary(
            operations_dashboard_summary_path,
            "daemon_loop.md",
        ),
        "notification_outbox_report": report_path_for_summary(
            operations_dashboard_summary_path,
            "notification_outbox.md",
        ),
        "state_export_report": report_path_for_summary(
            operations_dashboard_summary_path,
            "state_export.md",
        ),
        "state_restore_report": report_path_for_summary(
            operations_dashboard_summary_path,
            "state_restore.md",
        ),
        "live_evidence_report": live_evidence_report_path(
            live_evidence_summary_path,
            live_evidence,
        ),
    }


def _ops_summary_path(path: Path | None, summary_name: str) -> str | None:
    if path is None:
        return None
    return str(path.parent / summary_name)


def artifacts_from_paths(
    *,
    current_state_index_path: Path | None,
    phase_gate_summary_path: Path | None,
    execution_snapshot_summary_path: Path | None,
    execution_venue_comparison_summary_path: Path | None,
    execution_venue_diagnostics_summary_path: Path | None,
    execution_gap_history_summary_path: Path | None,
    execution_state_comparison_history_summary_path: Path | None,
    execution_snapshot_drift_history_summary_path: Path | None,
    execution_drift_overview_summary_path: Path | None,
    backtest_metrics_summary_path: Path | None,
    live_evidence_summary_path: Path | None,
    operations_dashboard_summary_path: Path | None,
    restart_pointers: Mapping[str, object],
) -> dict[str, object]:
    return {
        "current_state_index": _path_text(current_state_index_path),
        "phase_gate_summary": _path_text(phase_gate_summary_path),
        "execution_snapshot_summary": _path_text(execution_snapshot_summary_path),
        "execution_venue_comparison_summary": _path_text(execution_venue_comparison_summary_path),
        "execution_venue_diagnostics_summary": _path_text(execution_venue_diagnostics_summary_path),
        "execution_gap_history_summary": _path_text(execution_gap_history_summary_path),
        "execution_state_comparison_history_summary": _path_text(
            execution_state_comparison_history_summary_path
        ),
        "execution_snapshot_drift_history_summary": _path_text(
            execution_snapshot_drift_history_summary_path
        ),
        "execution_drift_overview_summary": _path_text(execution_drift_overview_summary_path),
        "backtest_metrics_summary": _path_text(backtest_metrics_summary_path),
        "live_evidence_summary": _path_text(live_evidence_summary_path),
        "operations_dashboard_summary": _path_text(operations_dashboard_summary_path),
        "live_evidence_report": restart_pointers.get("live_evidence_report"),
        **restart_pointers,
    }


def _path_text(path: Path | None) -> str | None:
    return str(path) if path is not None else None


def related_reports(
    restart_pointers: Mapping[str, object],
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
    return _string_items(ordered_items)


def quick_navigation(
    restart_pointers: Mapping[str, object],
    phase_gate_review_report_path: object,
) -> dict[str, str]:
    items = (
        ("readiness_snapshot_report", restart_pointers.get("readiness_snapshot_report")),
        ("current_state_index_report", restart_pointers.get("current_state_index_report")),
        ("phase_gate_review_report", phase_gate_review_report_path),
        ("remediation_scoreboard_report", restart_pointers.get("remediation_scoreboard_report")),
        ("live_evidence_report", restart_pointers.get("live_evidence_report")),
    )
    return _string_items(items)


def _string_items(items: tuple[tuple[str, object], ...]) -> dict[str, str]:
    return {key: value for key, value in items if isinstance(value, str) and value}
