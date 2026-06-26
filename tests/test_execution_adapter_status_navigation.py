from __future__ import annotations

from pathlib import Path

from sis.reports.execution_adapter_status_navigation import (
    execution_adapter_recommended_read_order,
    quick_navigation,
    related_reports,
    report_context,
)


def test_execution_adapter_recommended_read_order_includes_adapter_artifacts() -> None:
    assert execution_adapter_recommended_read_order() == [
        "docs/CURRENT_STATE.md",
        "docs/CODE_STATUS.md",
        "data/reports/execution_snapshot.md",
        "data/ops/current_state_index.json",
        "data/ops/readiness_snapshot.json",
        "data/ops/phase_gate_review_summary.json",
        "data/reports/current_state_index.md",
        "data/reports/readiness_snapshot.md",
        "data/reports/phase_gate_review.md",
        "data/reports/operations_dashboard.md",
        "data/reports/remediation_scoreboard.md",
        "docs/OPERATIONS_RUNBOOK.md",
        "docs/ARCHITECTURE_AND_PHASES.md",
    ]


def test_execution_adapter_quick_navigation_uses_report_siblings() -> None:
    out_path = Path("data/reports/execution_balance_status.md")

    assert quick_navigation(out_path) == {
        "execution_adapter_report": "data/reports/execution_balance_status.md",
        "execution_snapshot_report": "data/reports/execution_snapshot.md",
        "current_state_index_report": "data/reports/current_state_index.md",
        "readiness_snapshot_report": "data/reports/readiness_snapshot.md",
        "phase_gate_review_report": "data/reports/phase_gate_review.md",
        "remediation_scoreboard_report": "data/reports/remediation_scoreboard.md",
    }


def test_execution_adapter_related_reports_uses_expected_report_order() -> None:
    out_path = Path("data/reports/execution_balance_status.md")

    assert related_reports(out_path) == {
        "execution_snapshot_report": "data/reports/execution_snapshot.md",
        "execution_venue_comparison_report": "data/reports/execution_venue_comparison.md",
        "execution_venue_diagnostics_report": "data/reports/execution_venue_diagnostics.md",
        "execution_drift_overview_report": "data/reports/execution_drift_overview.md",
        "operations_dashboard_report": "data/reports/operations_dashboard.md",
        "current_state_index_report": "data/reports/current_state_index.md",
        "readiness_snapshot_report": "data/reports/readiness_snapshot.md",
        "phase_gate_review_report": "data/reports/phase_gate_review.md",
        "paper_operations_runbook_report": "data/reports/paper_operations_runbook.md",
        "remediation_scoreboard_report": "data/reports/remediation_scoreboard.md",
    }


def test_execution_adapter_navigation_handles_missing_output_path() -> None:
    assert quick_navigation(None) == {}
    assert related_reports(None) == {}


def test_execution_adapter_report_context_includes_read_order_and_navigation() -> None:
    out_path = Path("data/reports/execution_balance_status.md")

    assert report_context(out_path) == {
        "recommended_read_order": execution_adapter_recommended_read_order(),
        "quick_navigation": quick_navigation(out_path),
        "related_reports": related_reports(out_path),
    }


def test_execution_adapter_report_context_preserves_missing_output_shape() -> None:
    assert report_context(None) == {
        "recommended_read_order": execution_adapter_recommended_read_order(),
        "quick_navigation": {},
        "related_reports": {},
    }
