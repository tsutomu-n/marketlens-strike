from __future__ import annotations

from pathlib import Path
from typing import Mapping


def remediation_fields_from_sources(*sources: dict[str, object]) -> dict[str, object]:
    return {
        key: value
        for source in sources
        if isinstance(source, dict)
        for key, value in source.items()
        if isinstance(key, str) and key.startswith("timeline_latest_remediation_")
    }


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


def restart_pointers(
    *,
    operations_dashboard_summary_path: Path | None,
    live_evidence_summary_path: Path | None,
    live_evidence_summary: dict[str, object],
    out_path: Path | None,
) -> dict[str, str | None]:
    return {
        "current_state_index_report": str(out_path) if out_path is not None else None,
        "readiness_snapshot_report": report_path_for_summary(
            operations_dashboard_summary_path,
            "readiness_snapshot.md",
        ),
        "remediation_planner_summary": (
            str(operations_dashboard_summary_path.parent / "remediation_planner_summary.json")
            if operations_dashboard_summary_path is not None
            else None
        ),
        "remediation_planner_report": report_path_for_summary(
            operations_dashboard_summary_path,
            "remediation_planner.md",
        ),
        "remediation_execution_plan_summary": (
            str(
                operations_dashboard_summary_path.parent / "remediation_execution_plan_summary.json"
            )
            if operations_dashboard_summary_path is not None
            else None
        ),
        "remediation_execution_plan_report": report_path_for_summary(
            operations_dashboard_summary_path,
            "remediation_execution_plan.md",
        ),
        "remediation_session_summary": (
            str(operations_dashboard_summary_path.parent / "remediation_session_summary.json")
            if operations_dashboard_summary_path is not None
            else None
        ),
        "remediation_session_report": report_path_for_summary(
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
        "remediation_session_checkpoint_report": report_path_for_summary(
            operations_dashboard_summary_path,
            "remediation_session_checkpoint.md",
        ),
        "remediation_scoreboard_summary": (
            str(operations_dashboard_summary_path.parent / "remediation_scoreboard_summary.json")
            if operations_dashboard_summary_path is not None
            else None
        ),
        "remediation_scoreboard_report": report_path_for_summary(
            operations_dashboard_summary_path,
            "remediation_scoreboard.md",
        ),
        "remediation_evaluator_summary": (
            str(operations_dashboard_summary_path.parent / "remediation_evaluator_summary.json")
            if operations_dashboard_summary_path is not None
            else None
        ),
        "remediation_evaluator_report": report_path_for_summary(
            operations_dashboard_summary_path,
            "remediation_evaluator.md",
        ),
        "remediation_evidence_summary": (
            str(operations_dashboard_summary_path.parent / "remediation_evidence_summary.json")
            if operations_dashboard_summary_path is not None
            else None
        ),
        "remediation_evidence_report": report_path_for_summary(
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
        "remediation_command_results_report": report_path_for_summary(
            operations_dashboard_summary_path,
            "remediation_command_results.md",
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
            live_evidence_summary,
        ),
    }


def artifacts_from_paths(
    *,
    operations_dashboard_summary_path: Path | None,
    operations_bundle_manifest_path: Path | None,
    audit_dashboard_summary_path: Path | None,
    audit_bundle_manifest_path: Path | None,
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
    research_quality_report_path: Path | None,
    restart_pointers: Mapping[str, object],
) -> dict[str, object]:
    return {
        "operations_dashboard_summary": str(operations_dashboard_summary_path)
        if operations_dashboard_summary_path
        else None,
        "operations_bundle_manifest": str(operations_bundle_manifest_path)
        if operations_bundle_manifest_path
        else None,
        "audit_dashboard_summary": str(audit_dashboard_summary_path)
        if audit_dashboard_summary_path
        else None,
        "audit_bundle_manifest": str(audit_bundle_manifest_path)
        if audit_bundle_manifest_path
        else None,
        "phase_gate_summary": str(phase_gate_summary_path) if phase_gate_summary_path else None,
        "execution_snapshot_summary": str(execution_snapshot_summary_path)
        if execution_snapshot_summary_path
        else None,
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
            str(execution_drift_overview_summary_path)
            if execution_drift_overview_summary_path
            else None
        ),
        "backtest_metrics_summary": str(backtest_metrics_summary_path)
        if backtest_metrics_summary_path
        else None,
        "live_evidence_summary": str(live_evidence_summary_path)
        if live_evidence_summary_path
        else None,
        "live_evidence_report": restart_pointers.get("live_evidence_report"),
        "research_quality_report": str(research_quality_report_path)
        if research_quality_report_path
        else None,
        **restart_pointers,
    }


def related_reports(
    restart_pointers: Mapping[str, object],
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
    return _string_items(ordered_items)


def quick_navigation(
    restart_pointers: Mapping[str, object],
    phase_gate_review_report_path: object,
) -> dict[str, str]:
    items = (
        ("current_state_index_report", restart_pointers.get("current_state_index_report")),
        ("readiness_snapshot_report", restart_pointers.get("readiness_snapshot_report")),
        ("phase_gate_review_report", phase_gate_review_report_path),
        ("remediation_scoreboard_report", restart_pointers.get("remediation_scoreboard_report")),
        ("live_evidence_report", restart_pointers.get("live_evidence_report")),
    )
    return _string_items(items)


def _string_items(items: tuple[tuple[str, object], ...]) -> dict[str, str]:
    return {key: value for key, value in items if isinstance(value, str) and value}
