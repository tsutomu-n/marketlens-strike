from __future__ import annotations

from sis.reports.paper_operations_runbook_remediation import (
    build_paper_operations_runbook_remediation_context,
)


def test_runbook_remediation_context_builds_order_diffs_and_recommendations() -> None:
    summary = {
        "scheduled_run_path": None,
        "daemon_manifest_path": "data/ops/daemon_manifest.json",
        "monitoring_snapshot_path": "data/ops/monitoring.json",
        "execution_snapshot_summary_path": "data/ops/execution_snapshot.json",
        "execution_venue_comparison_summary_path": "data/ops/execution_comparison.json",
        "execution_venue_diagnostics_summary_path": "data/ops/execution_diagnostics.json",
        "execution_gap_history_summary_path": "data/ops/execution_gap_history.json",
        "execution_state_comparison_history_summary_path": (
            "data/ops/execution_state_comparison.json"
        ),
        "execution_snapshot_drift_history_summary_path": (
            "data/ops/execution_snapshot_drift.json"
        ),
        "execution_drift_overview_summary_path": "data/ops/execution_drift_overview.json",
        "readiness_summary_path": "data/ops/readiness.json",
        "phase_gate_summary_path": "data/ops/phase_gate.json",
        "ops_dashboard_summary_path": "data/ops/dashboard.json",
        "phase_gate_strict_validation_issue_count": 1,
        "phase_gate_checked_files": 7,
        "execution_diagnostics_status": "ok",
        "execution_balance_gap_detected": False,
        "execution_fills_gap_detected": False,
        "execution_drift_overview_status": "degraded",
        "execution_state_comparison_mismatching_count": 1,
        "execution_snapshot_drift_mismatching_snapshot_count": 1,
        "readiness_execution_ready": True,
        "phase2_entry_allowed": True,
    }
    prior_summary = {
        "remediation_signal_snapshots_before": {
            "execution_drift_unresolved": {
                "execution_drift_overview_status": "blocked",
                "execution_state_comparison_mismatching_count": 3,
                "execution_snapshot_drift_mismatching_snapshot_count": 2,
            }
        },
        "remediation_recommendations": {
            "strict_validation_failed": {
                "source_confidence": "medium",
                "source_policy": "structured_summary_priority",
            }
        },
    }
    planner_summary = {
        "entries": [
            {
                "source": "paper_operations_runbook",
                "reason": "execution_drift_unresolved",
                "source_confidence": "high",
                "source_policy": "direct_observation_priority",
            }
        ]
    }
    evaluator_summary = {
        "actions": [
            {
                "source": "paper_operations_runbook",
                "reason": "execution_drift_unresolved",
                "signal_evaluations": [
                    {
                        "signal": "execution_drift_overview_summary.json is regenerated",
                        "observed_source": "markdown_reports",
                    }
                ],
            }
        ]
    }

    context = build_paper_operations_runbook_remediation_context(
        summary=summary,
        prior_summary=prior_summary,
        planner_summary=planner_summary,
        evaluator_summary=evaluator_summary,
    )

    assert context["missing_required_artifact_paths"] == ["scheduled_run_path"]
    assert context["artifact_recovery_commands"] == {
        "scheduled_run_path": ["uv run sis schedule-run --run-type paper --when <ISO8601>"]
    }
    assert [item["reason"] for item in context["remediation_order"]] == [
        "missing_required_artifacts",
        "strict_validation_failed",
        "execution_drift_unresolved",
    ]
    assert context["remediation_success_criteria"]["strict_validation_failed"] == [
        "phase_gate_strict_validation_issue_count == 0"
    ]
    assert context["remediation_preflight_commands"]["missing_required_artifacts"] == [
        "uv run sis implementation-status"
    ]
    assert context["remediation_postcheck_commands"]["strict_validation_failed"] == [
        "uv run sis phase-gate-review",
        "uv run sis paper-operations-runbook",
    ]
    assert context["remediation_signal_snapshots_previous"] == prior_summary[
        "remediation_signal_snapshots_before"
    ]
    assert context["remediation_signal_snapshot_diffs"]["execution_drift_unresolved"][
        "execution_state_comparison_mismatching_count"
    ] == {
        "previous": 3,
        "current": 1,
        "target": 0,
        "trend": "changed",
        "target_matched": False,
    }
    assert context["remediation_recommendations"]["execution_drift_unresolved"] == {
        "status": "improving",
        "commands": ["uv run sis monitoring-status"],
        "why": "signals changed but low-confidence verification sources require revalidation before execute",
        "source_confidence": "high",
        "source_policy": "direct_observation_priority",
        "execute_signal_confidence": "low",
    }
    assert context["remediation_recommendations"]["strict_validation_failed"][
        "source_confidence"
    ] == "medium"


def test_runbook_remediation_context_handles_empty_order() -> None:
    summary = {
        "scheduled_run_path": "data/ops/scheduled_run.json",
        "daemon_manifest_path": "data/ops/daemon_manifest.json",
        "monitoring_snapshot_path": "data/ops/monitoring.json",
        "execution_snapshot_summary_path": "data/ops/execution_snapshot.json",
        "execution_venue_comparison_summary_path": "data/ops/execution_comparison.json",
        "execution_venue_diagnostics_summary_path": "data/ops/execution_diagnostics.json",
        "execution_gap_history_summary_path": "data/ops/execution_gap_history.json",
        "execution_state_comparison_history_summary_path": (
            "data/ops/execution_state_comparison.json"
        ),
        "execution_snapshot_drift_history_summary_path": (
            "data/ops/execution_snapshot_drift.json"
        ),
        "execution_drift_overview_summary_path": "data/ops/execution_drift_overview.json",
        "readiness_summary_path": "data/ops/readiness.json",
        "phase_gate_summary_path": "data/ops/phase_gate.json",
        "ops_dashboard_summary_path": "data/ops/dashboard.json",
        "phase_gate_strict_validation_issue_count": 0,
        "execution_diagnostics_status": "ok",
        "execution_drift_overview_status": "ok",
        "readiness_execution_ready": True,
    }

    context = build_paper_operations_runbook_remediation_context(
        summary=summary,
        prior_summary={},
        planner_summary={},
        evaluator_summary={},
    )

    assert context["missing_required_artifact_paths"] == []
    assert context["artifact_recovery_commands"] == {}
    assert context["remediation_order"] == []
    assert context["remediation_recommendations"] == {}
