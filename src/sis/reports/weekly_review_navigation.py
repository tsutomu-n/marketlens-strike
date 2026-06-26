from __future__ import annotations

from pathlib import Path
from typing import cast


def quick_navigation(out_path: Path | None, row: dict[str, object]) -> dict[str, str]:
    if out_path is None:
        return {}
    reports_dir = out_path.parent
    live_evidence_report_path = row.get("live_evidence_report_path")
    items: list[tuple[str, str | None]] = [
        ("weekly_review_report", str(out_path)),
        ("operations_dashboard_report", str(reports_dir / "operations_dashboard.md")),
        ("current_state_index_report", str(reports_dir / "current_state_index.md")),
        ("readiness_snapshot_report", str(reports_dir / "readiness_snapshot.md")),
        ("phase_gate_review_report", str(reports_dir / "phase_gate_review.md")),
        ("paper_operations_runbook_report", str(reports_dir / "paper_operations_runbook.md")),
        ("strategy_lifecycle_report", str(reports_dir / "strategy_lifecycle_report.md")),
        (
            "live_evidence_report",
            live_evidence_report_path if isinstance(live_evidence_report_path, str) else None,
        ),
    ]
    return {key: value for key, value in items if isinstance(value, str) and value}


def _nested_report_path(row: dict[str, object], section: str, flat_key: str) -> str | None:
    value = row.get(flat_key)
    if isinstance(value, str) and value:
        return value
    nested = row.get(section)
    if isinstance(nested, dict):
        nested_value = cast(dict[str, object], nested).get("report_path")
        if isinstance(nested_value, str) and nested_value:
            return nested_value
    return None


def related_reports(out_path: Path | None, row: dict[str, object]) -> dict[str, str]:
    if out_path is None:
        return {}
    reports_dir = out_path.parent
    live_evidence_report_path = row.get("live_evidence_report_path")
    items: list[tuple[str, str | None]] = [
        ("weekly_review_report", str(out_path)),
        ("operations_dashboard_report", str(reports_dir / "operations_dashboard.md")),
        ("ops_review_report", str(reports_dir / "ops_review.md")),
        ("current_state_index_report", str(reports_dir / "current_state_index.md")),
        ("readiness_snapshot_report", str(reports_dir / "readiness_snapshot.md")),
        ("phase_gate_review_report", str(reports_dir / "phase_gate_review.md")),
        ("go_no_go_report", str(out_path.parent.parent / "research/go_no_go_report.md")),
        ("paper_operations_runbook_report", str(reports_dir / "paper_operations_runbook.md")),
        ("strategy_lifecycle_report", str(reports_dir / "strategy_lifecycle_report.md")),
        (
            "paper_vs_backtest_comparison_report",
            str(reports_dir / "paper_vs_backtest_comparison.md"),
        ),
        (
            "execution_snapshot_report",
            _nested_report_path(row, "execution_summary", "execution_report_path"),
        ),
        (
            "execution_venue_comparison_report",
            _nested_report_path(
                row,
                "execution_comparison_summary",
                "execution_comparison_report_path",
            ),
        ),
        (
            "execution_venue_diagnostics_report",
            _nested_report_path(
                row,
                "execution_diagnostics_summary",
                "execution_diagnostics_report_path",
            ),
        ),
        (
            "execution_gap_history_report",
            _nested_report_path(
                row,
                "execution_gap_history_summary",
                "execution_gap_history_report_path",
            ),
        ),
        (
            "execution_state_comparison_report",
            _nested_report_path(
                row,
                "execution_state_comparison_summary",
                "execution_state_comparison_report_path",
            ),
        ),
        (
            "execution_snapshot_drift_report",
            _nested_report_path(
                row,
                "execution_snapshot_drift_summary",
                "execution_snapshot_drift_report_path",
            ),
        ),
        (
            "execution_drift_overview_report",
            _nested_report_path(
                row,
                "execution_drift_overview_summary",
                "execution_drift_overview_report_path",
            ),
        ),
        (
            "live_evidence_report",
            live_evidence_report_path if isinstance(live_evidence_report_path, str) else None,
        ),
    ]
    return {key: value for key, value in items if isinstance(value, str) and value}
