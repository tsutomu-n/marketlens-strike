from __future__ import annotations

from pathlib import Path

from sis.reports.paper_operations_runbook_summary import (
    build_paper_operations_runbook_base_summary,
)


def test_runbook_base_summary_builds_paths_normalized_fields_and_timeline_keys() -> None:
    summary = build_paper_operations_runbook_base_summary(
        scheduled_run_path=Path("data/ops/scheduled_run.json"),
        daemon_manifest_path=Path("data/ops/daemon_manifest.json"),
        monitoring_snapshot_path=None,
        execution_snapshot_summary_path=Path("data/ops/execution_snapshot.json"),
        execution_venue_comparison_summary_path=Path("data/ops/execution_comparison.json"),
        execution_venue_diagnostics_summary_path=Path("data/ops/execution_diagnostics.json"),
        execution_gap_history_summary_path=Path("data/ops/execution_gap_history.json"),
        execution_state_comparison_history_summary_path=Path(
            "data/ops/execution_state_comparison.json"
        ),
        execution_snapshot_drift_history_summary_path=Path(
            "data/ops/execution_snapshot_drift.json"
        ),
        execution_drift_overview_summary_path=Path("data/ops/execution_drift_overview.json"),
        readiness_summary_path=Path("data/ops/readiness.json"),
        phase_gate_summary_path=Path("data/ops/phase_gate.json"),
        ops_dashboard_summary_path=Path("data/ops/dashboard.json"),
        scheduled_run={
            "run_type": "paper",
            "scheduled_for": "2026-05-24T12:30:00+00:00",
            "command": "uv run sis paper-step",
        },
        daemon_manifest={"mode": "paper"},
        monitoring={"status": "ok"},
        execution={"overall_status": "ok", "venue_count": 2},
        execution_comparison={"all_registries_present": True},
        execution_diagnostics={
            "overall_status": "degraded",
            "balance_gap_detected": True,
            "fills_gap_detected": False,
        },
        execution_gap_history={
            "entry_count": 4,
            "latest_status": "ok",
            "latest_execution_diagnostics_status": "degraded",
        },
        execution_state_comparison={
            "entry_count": 4,
            "latest_status_match": False,
            "mismatching_count": 1,
        },
        execution_snapshot_drift={
            "entry_count": 3,
            "latest_execution_state_comparison_status_match": True,
            "mismatching_snapshot_count": 1,
        },
        execution_drift_overview={
            "overall_status": "degraded",
            "diagnostics_alignment_match": False,
            "state_comparison_mismatching_count": 1,
            "snapshot_drift_mismatching_snapshot_count": 1,
        },
        readiness={"next_phase_candidate": "Stay Phase 1", "execution_ready": False},
        phase_gate={
            "decision": "CONDITIONAL_GO_NEEDS_LIVE_WINDOW",
            "phase2_entry_allowed": False,
            "phase2_entry_reason": "remain_in_phase1_until_live_evidence_gate_clears",
            "strict_validation_issue_count": 2,
        },
        dashboard={
            "overall_status": "ok",
            "timeline_latest_execution_summary": {
                "execution_overall_status": "ok",
                "execution_venue_count": 2,
            },
            "bundle_history_latest_execution_summary": {
                "execution_overall_status": "degraded",
                "execution_venue_count": 1,
            },
            "cycle_history_latest_execution_comparison_summary": {
                "execution_comparison_all_registries_present": False,
            },
            "timeline_latest_remediation_planner_status": "stalled",
            "timeline_latest_remediation_session_next_pending_command": "uv run sis monitoring-status",
            "timeline_latest_remediation_scoreboard_next_action_command": "uv run sis phase-gate-review",
        },
    )

    assert summary["scheduled_run_type"] == "paper"
    assert summary["scheduled_command"] == "uv run sis paper-step"
    assert summary["scheduled_run_path"] == "data/ops/scheduled_run.json"
    assert summary["monitoring_snapshot_path"] is None
    assert summary["execution_snapshot_summary_path"] == "data/ops/execution_snapshot.json"
    assert summary["daemon_mode"] == "paper"
    assert summary["monitoring_status"] == "ok"
    assert summary["execution_overall_status"] == "ok"
    assert summary["execution_venue_count"] == 2
    assert summary["execution_comparison_all_registries_present"] is True
    assert summary["execution_diagnostics_status"] == "degraded"
    assert summary["execution_balance_gap_detected"] is True
    assert summary["execution_gap_history_entry_count"] == 4
    assert summary["execution_state_comparison_mismatching_count"] == 1
    assert summary["execution_snapshot_drift_mismatching_snapshot_count"] == 1
    assert summary["execution_drift_overview_status"] == "degraded"
    assert summary["readiness_next_phase_candidate"] == "Stay Phase 1"
    assert summary["readiness_execution_ready"] is False
    assert summary["phase_gate_decision"] == "CONDITIONAL_GO_NEEDS_LIVE_WINDOW"
    assert summary["phase_gate_strict_validation_issue_count"] == 2
    phase_gate_summary = summary["phase_gate_summary"]
    assert isinstance(phase_gate_summary, dict)
    assert phase_gate_summary["decision"] == "CONDITIONAL_GO_NEEDS_LIVE_WINDOW"
    assert phase_gate_summary["phase2_entry_allowed"] is False
    assert (
        phase_gate_summary["phase_gate_reason"]
        == "remain_in_phase1_until_live_evidence_gate_clears"
    )
    assert phase_gate_summary["phase_gate_strict_validation_issue_count"] == 2
    assert summary["timeline_latest_execution_overall_status"] == "ok"
    assert summary["bundle_history_latest_execution_overall_status"] == "degraded"
    assert summary["cycle_history_latest_execution_comparison_all_registries_present"] is False
    assert summary["timeline_latest_remediation_planner_status"] == "stalled"
    assert (
        summary["timeline_latest_remediation_session_next_pending_command"]
        == "uv run sis monitoring-status"
    )
    assert (
        summary["timeline_latest_remediation_scoreboard_next_action_command"]
        == "uv run sis phase-gate-review"
    )
    assert summary["dashboard_status"] == "ok"
