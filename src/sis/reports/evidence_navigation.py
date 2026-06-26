from __future__ import annotations

from pathlib import Path


def reports_dir(data_dir: Path) -> Path:
    return data_dir / "reports"


def quick_navigation(
    data_dir: Path,
    phase_gate_summary: dict[str, object],
    readiness_summary: dict[str, object],
) -> dict[str, str]:
    report_dir = reports_dir(data_dir)
    phase_gate_review_report_path = phase_gate_summary.get("phase_gate_review_report_path")
    live_evidence_report_path = readiness_summary.get("live_evidence_report_path")
    items: list[tuple[str, str | None]] = [
        ("evidence_card_report", None),
        (
            "go_no_go_report",
            str(data_dir / "research/go_no_go_report.md"),
        ),
        (
            "phase_gate_review_report",
            phase_gate_review_report_path
            if isinstance(phase_gate_review_report_path, str)
            else str(report_dir / "phase_gate_review.md"),
        ),
        ("current_state_index_report", str(report_dir / "current_state_index.md")),
        ("readiness_snapshot_report", str(report_dir / "readiness_snapshot.md")),
        ("paper_operations_runbook_report", str(report_dir / "paper_operations_runbook.md")),
        ("remediation_scoreboard_report", str(report_dir / "remediation_scoreboard.md")),
        (
            "live_evidence_report",
            live_evidence_report_path if isinstance(live_evidence_report_path, str) else None,
        ),
    ]
    return {key: value for key, value in items if isinstance(value, str) and value}


def related_reports(
    data_dir: Path,
    phase_gate_summary: dict[str, object],
    readiness_summary: dict[str, object],
    execution_summary: dict[str, object],
    execution_comparison_summary: dict[str, object],
    execution_diagnostics_summary: dict[str, object],
    execution_gap_history_summary: dict[str, object],
    execution_state_comparison_summary: dict[str, object],
    execution_snapshot_drift_summary: dict[str, object],
    execution_drift_overview_summary: dict[str, object],
) -> dict[str, str]:
    report_dir = reports_dir(data_dir)
    phase_gate_review_report_path = phase_gate_summary.get("phase_gate_review_report_path")
    live_evidence_report_path = readiness_summary.get("live_evidence_report_path")
    execution_report_path = execution_summary.get("report_path")
    execution_comparison_report_path = execution_comparison_summary.get("report_path")
    execution_diagnostics_report_path = execution_diagnostics_summary.get("report_path")
    execution_gap_history_report_path = execution_gap_history_summary.get("report_path")
    execution_state_comparison_report_path = execution_state_comparison_summary.get("report_path")
    execution_snapshot_drift_report_path = execution_snapshot_drift_summary.get("report_path")
    execution_drift_overview_report_path = execution_drift_overview_summary.get("report_path")
    items: list[tuple[str, str | None]] = [
        ("go_no_go_report", str(data_dir / "research/go_no_go_report.md")),
        (
            "phase_gate_review_report",
            phase_gate_review_report_path
            if isinstance(phase_gate_review_report_path, str)
            else str(report_dir / "phase_gate_review.md"),
        ),
        ("operations_dashboard_report", str(report_dir / "operations_dashboard.md")),
        ("ops_review_report", str(report_dir / "ops_review.md")),
        ("current_state_index_report", str(report_dir / "current_state_index.md")),
        ("readiness_snapshot_report", str(report_dir / "readiness_snapshot.md")),
        ("paper_operations_runbook_report", str(report_dir / "paper_operations_runbook.md")),
        (
            "paper_vs_backtest_comparison_report",
            str(report_dir / "paper_vs_backtest_comparison.md"),
        ),
        ("remediation_scoreboard_report", str(report_dir / "remediation_scoreboard.md")),
        (
            "live_evidence_report",
            live_evidence_report_path if isinstance(live_evidence_report_path, str) else None,
        ),
        (
            "execution_snapshot_report",
            execution_report_path if isinstance(execution_report_path, str) else None,
        ),
        (
            "execution_venue_comparison_report",
            execution_comparison_report_path
            if isinstance(execution_comparison_report_path, str)
            else None,
        ),
        (
            "execution_venue_diagnostics_report",
            execution_diagnostics_report_path
            if isinstance(execution_diagnostics_report_path, str)
            else None,
        ),
        (
            "execution_gap_history_report",
            execution_gap_history_report_path
            if isinstance(execution_gap_history_report_path, str)
            else None,
        ),
        (
            "execution_state_comparison_report",
            execution_state_comparison_report_path
            if isinstance(execution_state_comparison_report_path, str)
            else None,
        ),
        (
            "execution_snapshot_drift_report",
            execution_snapshot_drift_report_path
            if isinstance(execution_snapshot_drift_report_path, str)
            else None,
        ),
        (
            "execution_drift_overview_report",
            execution_drift_overview_report_path
            if isinstance(execution_drift_overview_report_path, str)
            else None,
        ),
    ]
    return {key: value for key, value in items if isinstance(value, str) and value}
