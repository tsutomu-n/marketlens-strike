from __future__ import annotations

from pathlib import Path


def report_path_for_summary(path: Path | None, report_name: str) -> str | None:
    if path is None:
        return None
    base = path.parent.parent if path.parent.name == "ops" else path.parent
    return str(base / "reports" / report_name)


def quick_navigation(summary: dict[str, object]) -> dict[str, str]:
    phase_gate_summary_path = _phase_gate_summary_path(summary)
    items = (
        ("audit_dashboard_report", summary.get("audit_dashboard_report_path")),
        (
            "current_state_index_report",
            report_path_for_summary(phase_gate_summary_path, "current_state_index.md"),
        ),
        (
            "readiness_snapshot_report",
            report_path_for_summary(phase_gate_summary_path, "readiness_snapshot.md"),
        ),
        ("phase_gate_review_report", summary.get("phase_gate_review_report_path")),
        (
            "remediation_scoreboard_report",
            report_path_for_summary(phase_gate_summary_path, "remediation_scoreboard.md"),
        ),
        (
            "operations_audit_pack_report",
            report_path_for_summary(phase_gate_summary_path, "operations_audit_pack.md"),
        ),
    )
    return _string_items(items)


def related_reports(summary: dict[str, object]) -> dict[str, str]:
    phase_gate_summary_path = _phase_gate_summary_path(summary)
    items = (
        ("audit_dashboard_report", summary.get("audit_dashboard_report_path")),
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
        ("phase_gate_review_report", summary.get("phase_gate_review_report_path")),
        (
            "operations_bundle_report",
            report_path_for_summary(phase_gate_summary_path, "operations_bundle_manifest.md"),
        ),
        (
            "audit_bundle_report",
            report_path_for_summary(phase_gate_summary_path, "audit_bundle_manifest.md"),
        ),
        (
            "operations_audit_pack_report",
            report_path_for_summary(phase_gate_summary_path, "operations_audit_pack.md"),
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
    return _string_items(items)


def _phase_gate_summary_path(summary: dict[str, object]) -> Path | None:
    phase_gate_summary_path_value = summary.get("phase_gate_summary_path")
    return (
        Path(phase_gate_summary_path_value)
        if isinstance(phase_gate_summary_path_value, str)
        else None
    )


def _string_items(items: tuple[tuple[str, object], ...]) -> dict[str, str]:
    return {key: value for key, value in items if isinstance(value, str) and value}
