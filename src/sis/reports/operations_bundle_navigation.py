from __future__ import annotations

from pathlib import Path


def report_path_for_summary(path: Path | None, report_name: str) -> str | None:
    if path is None:
        return None
    base = path.parent.parent if path.parent.name == "ops" else path.parent
    return str(base / "reports" / report_name)


def quick_navigation(phase_gate_summary_path: Path | None, out_path: Path | None) -> dict[str, str]:
    items = (
        ("operations_bundle_report", str(out_path) if out_path is not None else None),
        (
            "operations_dashboard_report",
            report_path_for_summary(phase_gate_summary_path, "operations_dashboard.md"),
        ),
        (
            "current_state_index_report",
            report_path_for_summary(phase_gate_summary_path, "current_state_index.md"),
        ),
        (
            "readiness_snapshot_report",
            report_path_for_summary(phase_gate_summary_path, "readiness_snapshot.md"),
        ),
        (
            "phase_gate_review_report",
            report_path_for_summary(phase_gate_summary_path, "phase_gate_review.md"),
        ),
        (
            "paper_operations_runbook_report",
            report_path_for_summary(phase_gate_summary_path, "paper_operations_runbook.md"),
        ),
        (
            "remediation_scoreboard_report",
            report_path_for_summary(phase_gate_summary_path, "remediation_scoreboard.md"),
        ),
    )
    return {key: value for key, value in items if isinstance(value, str) and value}


def related_reports(phase_gate_summary_path: Path | None, out_path: Path | None) -> dict[str, str]:
    items = (
        ("operations_bundle_report", str(out_path) if out_path is not None else None),
        (
            "operations_dashboard_report",
            report_path_for_summary(phase_gate_summary_path, "operations_dashboard.md"),
        ),
        (
            "audit_dashboard_report",
            report_path_for_summary(phase_gate_summary_path, "audit_dashboard.md"),
        ),
        (
            "operations_audit_pack_report",
            report_path_for_summary(phase_gate_summary_path, "operations_audit_pack.md"),
        ),
        (
            "ops_review_report",
            report_path_for_summary(phase_gate_summary_path, "ops_review_report.md"),
        ),
        (
            "current_state_index_report",
            report_path_for_summary(phase_gate_summary_path, "current_state_index.md"),
        ),
        (
            "readiness_snapshot_report",
            report_path_for_summary(phase_gate_summary_path, "readiness_snapshot.md"),
        ),
        (
            "phase_gate_review_report",
            report_path_for_summary(phase_gate_summary_path, "phase_gate_review.md"),
        ),
        (
            "paper_operations_runbook_report",
            report_path_for_summary(phase_gate_summary_path, "paper_operations_runbook.md"),
        ),
        (
            "remediation_scoreboard_report",
            report_path_for_summary(phase_gate_summary_path, "remediation_scoreboard.md"),
        ),
    )
    return {key: value for key, value in items if isinstance(value, str) and value}
