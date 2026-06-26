from __future__ import annotations

from pathlib import Path

from sis.reports.cost_matrix_navigation import quick_navigation, related_reports


def test_quick_navigation_omits_missing_output_path() -> None:
    assert quick_navigation(None) == {}


def test_quick_navigation_uses_cost_matrix_report_siblings_and_live_evidence_path() -> None:
    assert quick_navigation(Path("data/reports/venue_cost_matrix.md")) == {
        "venue_cost_matrix_report": "data/reports/venue_cost_matrix.md",
        "current_state_index_report": "data/reports/current_state_index.md",
        "readiness_snapshot_report": "data/reports/readiness_snapshot.md",
        "phase_gate_review_report": "data/reports/phase_gate_review.md",
        "live_evidence_report": "data/docs/live_evidence_reports/latest.md",
    }


def test_related_reports_omits_missing_output_path() -> None:
    assert related_reports(None) == {}


def test_related_reports_uses_cost_matrix_report_siblings_and_research_path() -> None:
    assert related_reports(Path("data/reports/venue_cost_matrix.md")) == {
        "venue_cost_matrix_report": "data/reports/venue_cost_matrix.md",
        "quote_diagnostics_report": "data/reports/quote_diagnostics.md",
        "execution_snapshot_report": "data/reports/execution_snapshot.md",
        "execution_venue_comparison_report": "data/reports/execution_venue_comparison.md",
        "execution_venue_diagnostics_report": "data/reports/execution_venue_diagnostics.md",
        "paper_operations_runbook_report": "data/reports/paper_operations_runbook.md",
        "go_no_go_report": "data/research/go_no_go_report.md",
        "current_state_index_report": "data/reports/current_state_index.md",
        "readiness_snapshot_report": "data/reports/readiness_snapshot.md",
    }
