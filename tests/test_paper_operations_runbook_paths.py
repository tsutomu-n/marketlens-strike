from __future__ import annotations

from pathlib import Path

from sis.reports.paper_operations_runbook_paths import (
    quick_navigation,
    related_reports,
    report_path_for_summary,
    required_artifact_paths,
)


def test_report_path_for_summary_uses_reports_sibling_for_ops_summary() -> None:
    assert report_path_for_summary(Path("data/ops/readiness_summary.json"), "report.md") == (
        "data/reports/report.md"
    )


def test_report_path_for_summary_uses_summary_parent_for_non_ops_path() -> None:
    assert report_path_for_summary(Path("tmp/readiness_summary.json"), "report.md") == (
        "tmp/reports/report.md"
    )


def test_report_path_for_summary_omits_missing_path() -> None:
    assert report_path_for_summary(None, "report.md") is None


def test_related_reports_derives_runbook_restart_report_order() -> None:
    summary = {
        "paper_operations_runbook_report_path": "data/reports/paper_operations_runbook.md",
        "readiness_summary_path": "data/ops/readiness_snapshot_summary.json",
        "phase_gate_review_report_path": "data/reports/phase_gate_review.md",
        "ops_dashboard_summary_path": "data/ops/operations_dashboard_summary.json",
        "live_evidence_report_path": "docs/live_evidence_reports/live_evidence_report_run-1.md",
    }

    assert related_reports(summary) == {
        "paper_operations_runbook_report": "data/reports/paper_operations_runbook.md",
        "readiness_snapshot_report": "data/reports/readiness_snapshot.md",
        "current_state_index_report": "data/reports/current_state_index.md",
        "phase_gate_review_report": "data/reports/phase_gate_review.md",
        "operations_dashboard_report": "data/reports/operations_dashboard.md",
        "ops_review_report": "data/reports/ops_review_report.md",
        "remediation_scoreboard_report": "data/reports/remediation_scoreboard.md",
        "remediation_session_checkpoint_report": ("data/reports/remediation_session_checkpoint.md"),
        "remediation_session_report": "data/reports/remediation_session.md",
        "remediation_execution_plan_report": ("data/reports/remediation_execution_plan.md"),
        "remediation_planner_report": "data/reports/remediation_planner.md",
        "live_evidence_report": "docs/live_evidence_reports/live_evidence_report_run-1.md",
    }


def test_quick_navigation_uses_related_reports_and_filters_missing_values() -> None:
    summary = {
        "paper_operations_runbook_report_path": "data/reports/paper_operations_runbook.md",
        "phase_gate_review_report_path": "data/reports/phase_gate_review.md",
        "live_evidence_report_path": "",
        "related_reports": {
            "readiness_snapshot_report": "data/reports/readiness_snapshot.md",
            "current_state_index_report": "data/reports/current_state_index.md",
            "remediation_scoreboard_report": "data/reports/remediation_scoreboard.md",
        },
    }

    assert quick_navigation(summary) == {
        "paper_operations_runbook_report": "data/reports/paper_operations_runbook.md",
        "readiness_snapshot_report": "data/reports/readiness_snapshot.md",
        "current_state_index_report": "data/reports/current_state_index.md",
        "phase_gate_review_report": "data/reports/phase_gate_review.md",
        "remediation_scoreboard_report": "data/reports/remediation_scoreboard.md",
    }


def test_required_artifact_paths_keeps_only_expected_string_artifacts() -> None:
    summary = {
        "scheduled_run_path": "data/ops/scheduled_run.json",
        "daemon_manifest_path": "data/ops/daemon_manifest.json",
        "monitoring_snapshot_path": None,
        "execution_snapshot_summary_path": "data/ops/execution_snapshot_summary.json",
        "execution_venue_comparison_summary_path": 123,
        "execution_venue_diagnostics_summary_path": "data/ops/diagnostics.json",
        "execution_gap_history_summary_path": "data/ops/gap_history.json",
        "execution_state_comparison_history_summary_path": "data/ops/state.json",
        "execution_snapshot_drift_history_summary_path": "data/ops/drift.json",
        "execution_drift_overview_summary_path": "data/ops/drift_overview.json",
        "readiness_summary_path": "data/ops/readiness_snapshot_summary.json",
        "phase_gate_summary_path": "data/ops/phase_gate_review_summary.json",
        "ops_dashboard_summary_path": "data/ops/operations_dashboard_summary.json",
        "unrelated": "ignored",
    }

    assert required_artifact_paths(summary) == {
        "scheduled_run_path": "data/ops/scheduled_run.json",
        "daemon_manifest_path": "data/ops/daemon_manifest.json",
        "monitoring_snapshot_path": None,
        "execution_snapshot_summary_path": "data/ops/execution_snapshot_summary.json",
        "execution_venue_comparison_summary_path": None,
        "execution_venue_diagnostics_summary_path": "data/ops/diagnostics.json",
        "execution_gap_history_summary_path": "data/ops/gap_history.json",
        "execution_state_comparison_history_summary_path": "data/ops/state.json",
        "execution_snapshot_drift_history_summary_path": "data/ops/drift.json",
        "execution_drift_overview_summary_path": "data/ops/drift_overview.json",
        "readiness_summary_path": "data/ops/readiness_snapshot_summary.json",
        "phase_gate_summary_path": "data/ops/phase_gate_review_summary.json",
        "ops_dashboard_summary_path": "data/ops/operations_dashboard_summary.json",
    }
