from __future__ import annotations

from pathlib import Path
from typing import cast


def report_path_for_summary(path: Path | None, report_name: str) -> str | None:
    if path is None:
        return None
    base = path.parent.parent if path.parent.name == "ops" else path.parent
    return str(base / "reports" / report_name)


def related_reports(summary: dict[str, object]) -> dict[str, str]:
    readiness_summary_path_value = summary.get("readiness_summary_path")
    readiness_summary_path = (
        Path(readiness_summary_path_value)
        if isinstance(readiness_summary_path_value, str)
        else None
    )
    ops_dashboard_summary_path_value = summary.get("ops_dashboard_summary_path")
    ops_dashboard_summary_path = (
        Path(ops_dashboard_summary_path_value)
        if isinstance(ops_dashboard_summary_path_value, str)
        else None
    )
    ordered_items = (
        (
            "paper_operations_runbook_report",
            summary.get("paper_operations_runbook_report_path"),
        ),
        (
            "readiness_snapshot_report",
            report_path_for_summary(readiness_summary_path, "readiness_snapshot.md"),
        ),
        (
            "current_state_index_report",
            report_path_for_summary(readiness_summary_path, "current_state_index.md"),
        ),
        ("phase_gate_review_report", summary.get("phase_gate_review_report_path")),
        (
            "operations_dashboard_report",
            report_path_for_summary(ops_dashboard_summary_path, "operations_dashboard.md"),
        ),
        (
            "ops_review_report",
            report_path_for_summary(ops_dashboard_summary_path, "ops_review_report.md"),
        ),
        (
            "remediation_scoreboard_report",
            report_path_for_summary(ops_dashboard_summary_path, "remediation_scoreboard.md"),
        ),
        (
            "remediation_session_checkpoint_report",
            report_path_for_summary(
                ops_dashboard_summary_path,
                "remediation_session_checkpoint.md",
            ),
        ),
        (
            "remediation_session_report",
            report_path_for_summary(ops_dashboard_summary_path, "remediation_session.md"),
        ),
        (
            "remediation_execution_plan_report",
            report_path_for_summary(
                ops_dashboard_summary_path,
                "remediation_execution_plan.md",
            ),
        ),
        (
            "remediation_planner_report",
            report_path_for_summary(ops_dashboard_summary_path, "remediation_planner.md"),
        ),
        ("live_evidence_report", summary.get("live_evidence_report_path")),
    )
    return {key: value for key, value in ordered_items if isinstance(value, str) and value}


def quick_navigation(summary: dict[str, object]) -> dict[str, str]:
    related_reports_value = summary.get("related_reports")
    report_links = (
        cast(dict[str, object], related_reports_value)
        if isinstance(related_reports_value, dict)
        else {}
    )
    items = (
        (
            "paper_operations_runbook_report",
            summary.get("paper_operations_runbook_report_path"),
        ),
        ("readiness_snapshot_report", report_links.get("readiness_snapshot_report")),
        ("current_state_index_report", report_links.get("current_state_index_report")),
        ("phase_gate_review_report", summary.get("phase_gate_review_report_path")),
        (
            "remediation_scoreboard_report",
            report_links.get("remediation_scoreboard_report"),
        ),
        ("live_evidence_report", summary.get("live_evidence_report_path")),
    )
    return {key: value for key, value in items if isinstance(value, str) and value}


def required_artifact_paths(summary: dict[str, object]) -> dict[str, str | None]:
    artifact_keys = (
        "scheduled_run_path",
        "daemon_manifest_path",
        "monitoring_snapshot_path",
        "execution_snapshot_summary_path",
        "execution_venue_comparison_summary_path",
        "execution_venue_diagnostics_summary_path",
        "execution_gap_history_summary_path",
        "execution_state_comparison_history_summary_path",
        "execution_snapshot_drift_history_summary_path",
        "execution_drift_overview_summary_path",
        "readiness_summary_path",
        "phase_gate_summary_path",
        "ops_dashboard_summary_path",
    )
    paths: dict[str, str | None] = {}
    for key in artifact_keys:
        value = summary.get(key)
        paths[key] = value if isinstance(value, str) else None
    return paths
