from __future__ import annotations

from pathlib import Path

from sis.reports.audit_dashboard_navigation import (
    quick_navigation,
    related_reports,
    report_path_for_summary,
)


def test_report_path_for_summary_uses_reports_sibling_for_ops_summary() -> None:
    assert report_path_for_summary(Path("data/ops/phase_gate_summary.json"), "audit.md") == (
        "data/reports/audit.md"
    )


def test_report_path_for_summary_uses_summary_parent_for_non_ops_path() -> None:
    assert report_path_for_summary(Path("tmp/phase_gate_summary.json"), "audit.md") == (
        "tmp/reports/audit.md"
    )


def test_report_path_for_summary_omits_missing_path() -> None:
    assert report_path_for_summary(None, "audit.md") is None


def test_quick_navigation_filters_missing_and_non_string_values() -> None:
    summary = {
        "audit_dashboard_report_path": "data/reports/audit_dashboard.md",
        "phase_gate_summary_path": "data/ops/phase_gate_summary.json",
        "phase_gate_review_report_path": "",
        "unexpected_non_string": 123,
    }

    assert quick_navigation(summary) == {
        "audit_dashboard_report": "data/reports/audit_dashboard.md",
        "current_state_index_report": "data/reports/current_state_index.md",
        "readiness_snapshot_report": "data/reports/readiness_snapshot.md",
        "remediation_scoreboard_report": "data/reports/remediation_scoreboard.md",
        "operations_audit_pack_report": "data/reports/operations_audit_pack.md",
    }


def test_related_reports_preserves_dashboard_report_order() -> None:
    summary = {
        "audit_dashboard_report_path": "data/reports/audit_dashboard.md",
        "phase_gate_summary_path": "data/ops/phase_gate_summary.json",
        "phase_gate_review_report_path": "data/reports/phase_gate_review.md",
    }

    assert related_reports(summary) == {
        "audit_dashboard_report": "data/reports/audit_dashboard.md",
        "operations_dashboard_report": "data/reports/operations_dashboard.md",
        "current_state_index_report": "data/reports/current_state_index.md",
        "readiness_snapshot_report": "data/reports/readiness_snapshot.md",
        "phase_gate_review_report": "data/reports/phase_gate_review.md",
        "operations_bundle_report": "data/reports/operations_bundle_manifest.md",
        "audit_bundle_report": "data/reports/audit_bundle_manifest.md",
        "operations_audit_pack_report": "data/reports/operations_audit_pack.md",
        "paper_operations_runbook_report": "data/reports/paper_operations_runbook.md",
        "remediation_scoreboard_report": "data/reports/remediation_scoreboard.md",
    }
