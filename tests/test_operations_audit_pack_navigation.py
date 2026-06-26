from pathlib import Path

from sis.reports.operations_audit_pack_navigation import (
    quick_navigation,
    related_reports,
    report_path_for_summary,
)


def test_report_path_for_summary_uses_reports_sibling_for_ops_summary() -> None:
    assert (
        report_path_for_summary(Path("data/ops/phase_gate_review_summary.json"), "audit.md")
        == "data/reports/audit.md"
    )


def test_report_path_for_summary_uses_summary_parent_for_non_ops_path() -> None:
    assert (
        report_path_for_summary(Path("data/custom/phase_gate_review_summary.json"), "audit.md")
        == "data/custom/reports/audit.md"
    )


def test_report_path_for_summary_omits_missing_path() -> None:
    assert report_path_for_summary(None, "audit.md") is None


def test_quick_navigation_filters_missing_values_and_preserves_order() -> None:
    navigation = quick_navigation(
        Path("data/ops/phase_gate_review_summary.json"),
        Path("data/reports/operations_audit_pack.md"),
    )

    assert navigation == {
        "operations_audit_pack_report": "data/reports/operations_audit_pack.md",
        "operations_dashboard_report": "data/reports/operations_dashboard.md",
        "audit_dashboard_report": "data/reports/audit_dashboard.md",
        "current_state_index_report": "data/reports/current_state_index.md",
        "readiness_snapshot_report": "data/reports/readiness_snapshot.md",
        "phase_gate_review_report": "data/reports/phase_gate_review.md",
        "remediation_scoreboard_report": "data/reports/remediation_scoreboard.md",
    }


def test_quick_navigation_omits_all_missing_paths() -> None:
    assert quick_navigation(None, None) == {}


def test_related_reports_preserves_expected_order() -> None:
    reports = related_reports(
        Path("data/ops/phase_gate_review_summary.json"),
        Path("data/reports/operations_audit_pack.md"),
    )

    assert reports == {
        "operations_audit_pack_report": "data/reports/operations_audit_pack.md",
        "operations_bundle_report": "data/reports/operations_bundle.md",
        "audit_bundle_report": "data/reports/audit_bundle.md",
        "operations_dashboard_report": "data/reports/operations_dashboard.md",
        "audit_dashboard_report": "data/reports/audit_dashboard.md",
        "current_state_index_report": "data/reports/current_state_index.md",
        "readiness_snapshot_report": "data/reports/readiness_snapshot.md",
        "phase_gate_review_report": "data/reports/phase_gate_review.md",
        "paper_operations_runbook_report": "data/reports/paper_operations_runbook.md",
    }
