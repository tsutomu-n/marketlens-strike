from __future__ import annotations

from pathlib import Path

from sis.reports.remediation_evaluator_paths import (
    current_state_index_paths,
    dashboard_bundle_summary_paths,
    ops_review_paths,
    quick_navigation,
    related_reports,
    report_path_from_summary_path,
    report_paths,
    timeline_summary_paths,
)


def test_quick_navigation_omits_missing_out_path() -> None:
    assert quick_navigation(None) == {}


def test_quick_navigation_uses_reports_siblings() -> None:
    out_path = Path("data/reports/remediation_evaluator.md")

    assert quick_navigation(out_path) == {
        "remediation_evaluator_report": "data/reports/remediation_evaluator.md",
        "remediation_evidence_report": "data/reports/remediation_evidence.md",
        "remediation_scoreboard_report": "data/reports/remediation_scoreboard.md",
        "remediation_session_checkpoint_report": ("data/reports/remediation_session_checkpoint.md"),
        "current_state_index_report": "data/reports/current_state_index.md",
    }


def test_related_reports_uses_expected_report_order() -> None:
    out_path = Path("data/reports/remediation_evaluator.md")

    assert related_reports(out_path) == {
        "remediation_evaluator_report": "data/reports/remediation_evaluator.md",
        "remediation_planner_report": "data/reports/remediation_planner.md",
        "remediation_execution_plan_report": "data/reports/remediation_execution_plan.md",
        "remediation_session_report": "data/reports/remediation_session.md",
        "remediation_session_checkpoint_report": ("data/reports/remediation_session_checkpoint.md"),
        "remediation_scoreboard_report": "data/reports/remediation_scoreboard.md",
        "remediation_evidence_report": "data/reports/remediation_evidence.md",
        "remediation_command_results_report": "data/reports/remediation_command_results.md",
        "phase_gate_review_report": "data/reports/phase_gate_review.md",
        "paper_operations_runbook_report": "data/reports/paper_operations_runbook.md",
        "current_state_index_report": "data/reports/current_state_index.md",
        "readiness_snapshot_report": "data/reports/readiness_snapshot.md",
    }


def test_report_path_from_summary_path_handles_ops_summary_names() -> None:
    assert report_path_from_summary_path(Path("data/ops/phase_gate_review_summary.json")) == Path(
        "data/reports/phase_gate_review.md"
    )
    assert report_path_from_summary_path(Path("data/ops/ops_review_summary.json")) == Path(
        "data/reports/ops_review_report.md"
    )
    assert report_path_from_summary_path(Path("data/other/phase_gate_review_summary.json")) is None


def test_report_paths_prefers_explicit_summary_report_paths() -> None:
    planner = {
        "phase_gate_summary_path": "data/ops/phase_gate_review_summary.json",
        "runbook_summary_path": "data/ops/paper_operations_runbook_summary.json",
    }
    source_summaries = {
        "phase_gate_review": {
            "phase_gate_review_report_path": "custom/phase_gate_review.md",
        },
        "paper_operations_runbook": {},
    }

    assert report_paths(planner, source_summaries) == {
        "phase_gate_review": Path("custom/phase_gate_review.md"),
        "paper_operations_runbook": Path("data/reports/paper_operations_runbook.md"),
    }


def test_planner_derived_paths_use_first_available_base_dir() -> None:
    planner = {"phase_gate_summary_path": "data/ops/phase_gate_review_summary.json"}

    assert timeline_summary_paths(planner) == {
        "operations_timeline": Path("data/ops/operations_timeline_summary.json"),
        "audit_timeline": Path("data/ops/audit_timeline_summary.json"),
    }
    assert dashboard_bundle_summary_paths(planner) == {
        "operations_dashboard": Path("data/ops/operations_dashboard_summary.json"),
        "audit_dashboard": Path("data/ops/audit_dashboard_summary.json"),
        "operations_bundle": Path("data/ops/operations_bundle_manifest.json"),
        "operations_audit_pack": Path("data/ops/operations_audit_pack.json"),
        "audit_bundle": Path("data/ops/audit_bundle_manifest.json"),
    }
    assert ops_review_paths(planner) == {
        "ops_review_summary": Path("data/ops/ops_review_summary.json"),
        "ops_review_report": Path("data/reports/ops_review_report.md"),
    }
    assert current_state_index_paths(planner) == {
        "current_state_index_summary": Path("data/ops/current_state_index.json"),
        "current_state_index_report": Path("data/reports/current_state_index.md"),
    }


def test_planner_derived_paths_fall_back_to_runbook_base_dir() -> None:
    planner = {"runbook_summary_path": "data/ops/paper_operations_runbook_summary.json"}

    assert timeline_summary_paths(planner)["operations_timeline"] == Path(
        "data/ops/operations_timeline_summary.json"
    )
