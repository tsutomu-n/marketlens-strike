from pathlib import Path

from sis.reports.audit_bundle_navigation import (
    quick_navigation,
    related_reports,
    report_path_for_summary,
)


def test_report_path_for_summary_omits_missing_summary_path() -> None:
    assert report_path_for_summary(None, "phase_gate_review.md") is None


def test_report_path_for_summary_uses_reports_sibling_for_ops_summary() -> None:
    assert (
        report_path_for_summary(
            Path("data/ops/phase_gate_review_summary.json"),
            "phase_gate_review.md",
        )
        == "data/reports/phase_gate_review.md"
    )


def test_report_path_for_summary_uses_reports_child_for_non_ops_summary() -> None:
    assert (
        report_path_for_summary(
            Path("data/custom/phase_gate_review_summary.json"),
            "phase_gate_review.md",
        )
        == "data/custom/reports/phase_gate_review.md"
    )


def test_quick_navigation_omits_all_missing_paths() -> None:
    assert quick_navigation(None, None) == {}


def test_quick_navigation_keeps_output_report_when_phase_gate_is_missing() -> None:
    assert quick_navigation(None, Path("data/reports/audit_bundle_manifest.md")) == {
        "audit_bundle_report": "data/reports/audit_bundle_manifest.md",
    }


def test_quick_navigation_uses_phase_gate_report_siblings() -> None:
    phase_gate_summary = Path("data/ops/phase_gate_review_summary.json")
    out_path = Path("data/reports/audit_bundle_manifest.md")

    assert quick_navigation(phase_gate_summary, out_path) == {
        "audit_bundle_report": "data/reports/audit_bundle_manifest.md",
        "audit_dashboard_report": "data/reports/audit_dashboard.md",
        "operations_dashboard_report": "data/reports/operations_dashboard.md",
        "operations_audit_pack_report": "data/reports/operations_audit_pack.md",
        "current_state_index_report": "data/reports/current_state_index.md",
        "readiness_snapshot_report": "data/reports/readiness_snapshot.md",
        "phase_gate_review_report": "data/reports/phase_gate_review.md",
    }


def test_related_reports_uses_expected_report_siblings() -> None:
    phase_gate_summary = Path("data/ops/phase_gate_review_summary.json")
    out_path = Path("data/reports/audit_bundle_manifest.md")

    assert related_reports(phase_gate_summary, out_path) == {
        "audit_bundle_report": "data/reports/audit_bundle_manifest.md",
        "audit_dashboard_report": "data/reports/audit_dashboard.md",
        "operations_dashboard_report": "data/reports/operations_dashboard.md",
        "operations_bundle_report": "data/reports/operations_bundle.md",
        "operations_audit_pack_report": "data/reports/operations_audit_pack.md",
        "current_state_index_report": "data/reports/current_state_index.md",
        "readiness_snapshot_report": "data/reports/readiness_snapshot.md",
        "phase_gate_review_report": "data/reports/phase_gate_review.md",
        "paper_operations_runbook_report": "data/reports/paper_operations_runbook.md",
    }
