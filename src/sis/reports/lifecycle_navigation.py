from __future__ import annotations

from pathlib import Path
from typing import cast


def quick_navigation(
    out_path: Path | None,
    payload: dict[str, object],
) -> dict[str, str]:
    if out_path is None:
        return {}
    reports_dir = out_path.parent
    live_evidence_report_path = payload.get("live_evidence_report_path")
    items: list[tuple[str, str | None]] = [
        ("strategy_lifecycle_report", str(out_path)),
        ("weekly_review_report", str(reports_dir / "weekly_strategy_review.md")),
        ("operations_dashboard_report", str(reports_dir / "operations_dashboard.md")),
        ("current_state_index_report", str(reports_dir / "current_state_index.md")),
        ("readiness_snapshot_report", str(reports_dir / "readiness_snapshot.md")),
        ("phase_gate_review_report", str(reports_dir / "phase_gate_review.md")),
        ("paper_operations_runbook_report", str(reports_dir / "paper_operations_runbook.md")),
        (
            "live_evidence_report",
            live_evidence_report_path if isinstance(live_evidence_report_path, str) else None,
        ),
    ]
    return {key: value for key, value in items if isinstance(value, str) and value}


def nested_report_path(payload: dict[str, object], section: str, flat_key: str) -> str | None:
    value = payload.get(flat_key)
    if isinstance(value, str) and value:
        return value
    nested = payload.get(section)
    if isinstance(nested, dict):
        nested_value = cast(dict[str, object], nested).get("report_path")
        if isinstance(nested_value, str) and nested_value:
            return nested_value
    return None


def related_reports(out_path: Path | None, payload: dict[str, object]) -> dict[str, str]:
    if out_path is None:
        return {}
    reports_dir = out_path.parent
    live_evidence_report_path = payload.get("live_evidence_report_path")
    items: list[tuple[str, str | None]] = [
        ("strategy_lifecycle_report", str(out_path)),
        ("weekly_review_report", str(reports_dir / "weekly_strategy_review.md")),
        ("operations_dashboard_report", str(reports_dir / "operations_dashboard.md")),
        ("ops_review_report", str(reports_dir / "ops_review.md")),
        ("current_state_index_report", str(reports_dir / "current_state_index.md")),
        ("readiness_snapshot_report", str(reports_dir / "readiness_snapshot.md")),
        ("phase_gate_review_report", str(reports_dir / "phase_gate_review.md")),
        ("go_no_go_report", str(out_path.parent.parent / "research/go_no_go_report.md")),
        ("paper_operations_runbook_report", str(reports_dir / "paper_operations_runbook.md")),
        (
            "paper_vs_backtest_comparison_report",
            str(reports_dir / "paper_vs_backtest_comparison.md"),
        ),
        (
            "execution_drift_overview_report",
            nested_report_path(
                payload,
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
