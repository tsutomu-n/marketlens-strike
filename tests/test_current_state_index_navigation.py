from __future__ import annotations

from pathlib import Path

from sis.reports.current_state_index_navigation import (
    artifacts_from_paths,
    live_evidence_report_path,
    quick_navigation,
    related_reports,
    remediation_fields_from_sources,
    report_path_for_summary,
    restart_pointers,
)


def test_remediation_fields_from_sources_later_sources_override_earlier() -> None:
    operations_dashboard = {
        "timeline_latest_remediation_planner_status": "operations-dashboard",
        "timeline_latest_remediation_session_status": "operations-dashboard-session",
    }
    operations_bundle = {
        "timeline_latest_remediation_planner_status": "operations-bundle",
    }
    audit_dashboard = {
        "timeline_latest_remediation_planner_status": "audit-dashboard",
    }
    audit_bundle = {
        "timeline_latest_remediation_planner_status": "audit-bundle",
        "unrelated": "ignored",
    }

    assert remediation_fields_from_sources(
        operations_dashboard,
        operations_bundle,
        audit_dashboard,
        audit_bundle,
    ) == {
        "timeline_latest_remediation_planner_status": "audit-bundle",
        "timeline_latest_remediation_session_status": "operations-dashboard-session",
    }


def test_report_path_for_summary_uses_reports_sibling_for_ops_summary() -> None:
    assert report_path_for_summary(Path("data/ops/current_state_index.json"), "audit.md") == (
        "data/reports/audit.md"
    )


def test_report_path_for_summary_uses_summary_parent_for_non_ops_path() -> None:
    assert report_path_for_summary(Path("tmp/current_state_index.json"), "audit.md") == (
        "tmp/reports/audit.md"
    )


def test_report_path_for_summary_omits_missing_path() -> None:
    assert report_path_for_summary(None, "audit.md") is None


def test_live_evidence_report_path_prefers_summary_run_id() -> None:
    assert (
        live_evidence_report_path(
            Path("data/ops/live_evidence_summary_from-path.json"),
            {"run_id": "from-summary"},
        )
        == "docs/live_evidence_reports/live_evidence_report_from-summary.md"
    )


def test_live_evidence_report_path_falls_back_to_summary_filename() -> None:
    assert (
        live_evidence_report_path(
            Path("data/ops/live_evidence_summary_from-path.json"),
            {},
        )
        == "docs/live_evidence_reports/live_evidence_report_from-path.md"
    )


def test_live_evidence_report_path_omits_unrecognized_filename() -> None:
    assert live_evidence_report_path(Path("data/ops/latest_live_evidence.json"), {}) is None


def test_quick_navigation_filters_to_primary_current_state_reports() -> None:
    restart_pointers = {
        "current_state_index_report": "data/reports/current_state_index.md",
        "readiness_snapshot_report": "data/reports/readiness_snapshot.md",
        "remediation_scoreboard_report": "",
        "live_evidence_report": "docs/live_evidence_reports/live_evidence_report_run-1.md",
        "remediation_evaluator_report": "data/reports/remediation_evaluator.md",
    }

    assert quick_navigation(restart_pointers, "data/reports/phase_gate_review.md") == {
        "current_state_index_report": "data/reports/current_state_index.md",
        "readiness_snapshot_report": "data/reports/readiness_snapshot.md",
        "phase_gate_review_report": "data/reports/phase_gate_review.md",
        "live_evidence_report": "docs/live_evidence_reports/live_evidence_report_run-1.md",
    }


def test_related_reports_includes_ordered_current_state_restart_reports() -> None:
    restart_pointers = {
        "current_state_index_report": "data/reports/current_state_index.md",
        "readiness_snapshot_report": "data/reports/readiness_snapshot.md",
        "remediation_scoreboard_report": "data/reports/remediation_scoreboard.md",
        "remediation_session_checkpoint_report": "data/reports/remediation_session_checkpoint.md",
        "remediation_session_report": "data/reports/remediation_session.md",
        "remediation_execution_plan_report": "data/reports/remediation_execution_plan.md",
        "remediation_planner_report": "data/reports/remediation_planner.md",
        "remediation_evaluator_report": "data/reports/remediation_evaluator.md",
        "remediation_evidence_report": "data/reports/remediation_evidence.md",
        "remediation_command_results_report": "data/reports/remediation_command_results.md",
        "live_evidence_report": "docs/live_evidence_reports/live_evidence_report_run-1.md",
    }

    assert related_reports(restart_pointers, "data/reports/phase_gate_review.md") == {
        "current_state_index_report": "data/reports/current_state_index.md",
        "readiness_snapshot_report": "data/reports/readiness_snapshot.md",
        "phase_gate_review_report": "data/reports/phase_gate_review.md",
        "remediation_scoreboard_report": "data/reports/remediation_scoreboard.md",
        "remediation_session_checkpoint_report": "data/reports/remediation_session_checkpoint.md",
        "remediation_session_report": "data/reports/remediation_session.md",
        "remediation_execution_plan_report": "data/reports/remediation_execution_plan.md",
        "remediation_planner_report": "data/reports/remediation_planner.md",
        "remediation_evaluator_report": "data/reports/remediation_evaluator.md",
        "remediation_evidence_report": "data/reports/remediation_evidence.md",
        "remediation_command_results_report": "data/reports/remediation_command_results.md",
        "live_evidence_report": "docs/live_evidence_reports/live_evidence_report_run-1.md",
    }


def test_restart_pointers_preserve_ordered_current_state_report_paths() -> None:
    pointers = restart_pointers(
        operations_dashboard_summary_path=Path("data/ops/operations_dashboard_summary.json"),
        live_evidence_summary_path=Path("data/ops/live_evidence_summary_path-run.json"),
        live_evidence_summary={"run_id": "summary-run"},
        out_path=Path("data/reports/current_state_index.md"),
    )

    assert pointers == {
        "current_state_index_report": "data/reports/current_state_index.md",
        "readiness_snapshot_report": "data/reports/readiness_snapshot.md",
        "remediation_planner_summary": "data/ops/remediation_planner_summary.json",
        "remediation_planner_report": "data/reports/remediation_planner.md",
        "remediation_execution_plan_summary": "data/ops/remediation_execution_plan_summary.json",
        "remediation_execution_plan_report": "data/reports/remediation_execution_plan.md",
        "remediation_session_summary": "data/ops/remediation_session_summary.json",
        "remediation_session_report": "data/reports/remediation_session.md",
        "remediation_session_checkpoint_summary": (
            "data/ops/remediation_session_checkpoint_summary.json"
        ),
        "remediation_session_checkpoint_report": ("data/reports/remediation_session_checkpoint.md"),
        "remediation_scoreboard_summary": "data/ops/remediation_scoreboard_summary.json",
        "remediation_scoreboard_report": "data/reports/remediation_scoreboard.md",
        "remediation_evaluator_summary": "data/ops/remediation_evaluator_summary.json",
        "remediation_evaluator_report": "data/reports/remediation_evaluator.md",
        "remediation_evidence_summary": "data/ops/remediation_evidence_summary.json",
        "remediation_evidence_report": "data/reports/remediation_evidence.md",
        "remediation_command_results_summary": (
            "data/ops/remediation_command_results_summary.json"
        ),
        "remediation_command_results_report": ("data/reports/remediation_command_results.md"),
        "execution_balance_status_report": "data/reports/execution_balance_status.md",
        "execution_fill_status_report": "data/reports/execution_fill_status.md",
        "execution_order_status_report": "data/reports/execution_order_status.md",
        "execution_cancel_order_report": "data/reports/execution_cancel_order.md",
        "execution_close_position_report": "data/reports/execution_close_position.md",
        "execution_reconcile_positions_report": ("data/reports/execution_reconcile_positions.md"),
        "daemon_manifest_report": "data/reports/daemon_manifest.md",
        "daemon_loop_report": "data/reports/daemon_loop.md",
        "notification_outbox_report": "data/reports/notification_outbox.md",
        "state_export_report": "data/reports/state_export.md",
        "state_restore_report": "data/reports/state_restore.md",
        "live_evidence_report": ("docs/live_evidence_reports/live_evidence_report_summary-run.md"),
    }


def test_restart_pointers_preserve_none_shape_for_missing_paths() -> None:
    pointers = restart_pointers(
        operations_dashboard_summary_path=None,
        live_evidence_summary_path=None,
        live_evidence_summary={},
        out_path=None,
    )

    assert len(pointers) == 30
    assert pointers["current_state_index_report"] is None
    assert pointers["readiness_snapshot_report"] is None
    assert pointers["remediation_planner_summary"] is None
    assert pointers["execution_balance_status_report"] is None
    assert pointers["live_evidence_report"] is None


def test_artifacts_from_paths_preserves_input_paths_restart_pointers_and_order() -> None:
    pointers = {
        "current_state_index_report": "data/reports/current_state_index.md",
        "live_evidence_report": "docs/live_evidence_reports/live_evidence_report_run-1.md",
    }

    artifacts = artifacts_from_paths(
        operations_dashboard_summary_path=Path("data/ops/operations_dashboard_summary.json"),
        operations_bundle_manifest_path=Path("data/ops/operations_bundle_manifest.json"),
        audit_dashboard_summary_path=Path("data/ops/audit_dashboard_summary.json"),
        audit_bundle_manifest_path=Path("data/ops/audit_bundle_manifest.json"),
        phase_gate_summary_path=Path("data/ops/phase_gate_review_summary.json"),
        execution_snapshot_summary_path=Path("data/ops/execution_snapshot_summary.json"),
        execution_venue_comparison_summary_path=Path(
            "data/ops/execution_venue_comparison_summary.json"
        ),
        execution_venue_diagnostics_summary_path=Path(
            "data/ops/execution_venue_diagnostics_summary.json"
        ),
        execution_gap_history_summary_path=Path("data/ops/execution_gap_history_summary.json"),
        execution_state_comparison_history_summary_path=Path(
            "data/ops/execution_state_comparison_history_summary.json"
        ),
        execution_snapshot_drift_history_summary_path=Path(
            "data/ops/execution_snapshot_drift_history_summary.json"
        ),
        execution_drift_overview_summary_path=Path(
            "data/ops/execution_drift_overview_summary.json"
        ),
        backtest_metrics_summary_path=Path("data/research/backtest_metrics_summary.json"),
        live_evidence_summary_path=Path("data/ops/live_evidence_summary_run-1.json"),
        research_quality_report_path=Path("data/reports/research_quality.md"),
        restart_pointers=pointers,
    )

    assert artifacts == {
        "operations_dashboard_summary": "data/ops/operations_dashboard_summary.json",
        "operations_bundle_manifest": "data/ops/operations_bundle_manifest.json",
        "audit_dashboard_summary": "data/ops/audit_dashboard_summary.json",
        "audit_bundle_manifest": "data/ops/audit_bundle_manifest.json",
        "phase_gate_summary": "data/ops/phase_gate_review_summary.json",
        "execution_snapshot_summary": "data/ops/execution_snapshot_summary.json",
        "execution_venue_comparison_summary": ("data/ops/execution_venue_comparison_summary.json"),
        "execution_venue_diagnostics_summary": (
            "data/ops/execution_venue_diagnostics_summary.json"
        ),
        "execution_gap_history_summary": "data/ops/execution_gap_history_summary.json",
        "execution_state_comparison_history_summary": (
            "data/ops/execution_state_comparison_history_summary.json"
        ),
        "execution_snapshot_drift_history_summary": (
            "data/ops/execution_snapshot_drift_history_summary.json"
        ),
        "execution_drift_overview_summary": ("data/ops/execution_drift_overview_summary.json"),
        "backtest_metrics_summary": "data/research/backtest_metrics_summary.json",
        "live_evidence_summary": "data/ops/live_evidence_summary_run-1.json",
        "live_evidence_report": "docs/live_evidence_reports/live_evidence_report_run-1.md",
        "research_quality_report": "data/reports/research_quality.md",
        "current_state_index_report": "data/reports/current_state_index.md",
    }
