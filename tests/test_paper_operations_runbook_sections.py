from __future__ import annotations

from sis.reports.paper_operations_runbook_sections import (
    current_daemon_context_section_lines,
    current_remediation_queue_section_lines,
    current_schedule_section_lines,
    current_status_section_lines,
)


def _summary() -> dict[str, object]:
    return {
        "scheduled_run_type": "paper",
        "scheduled_for": "2026-05-24T12:30:00+00:00",
        "scheduled_command": "uv run sis paper-step",
        "daemon_mode": "paper",
        "daemon_manifest_path": "data/ops/daemon_manifest.json",
        "monitoring_status": "ok",
        "execution_overall_status": "ok",
        "execution_venue_count": 2,
        "execution_comparison_all_registries_present": True,
        "execution_diagnostics_status": "degraded",
        "execution_balance_gap_detected": True,
        "execution_fills_gap_detected": False,
        "execution_gap_history_entry_count": 4,
        "execution_gap_history_latest_status": "ok",
        "execution_gap_history_latest_diagnostics_status": "degraded",
        "execution_state_comparison_entry_count": 5,
        "execution_state_comparison_latest_status_match": False,
        "execution_state_comparison_mismatching_count": 1,
        "execution_snapshot_drift_entry_count": 3,
        "execution_snapshot_drift_latest_status_match": True,
        "execution_snapshot_drift_mismatching_snapshot_count": 1,
        "execution_drift_overview_status": "degraded",
        "execution_drift_overview_diagnostics_alignment_match": False,
        "execution_drift_overview_state_comparison_mismatching_count": 1,
        "execution_drift_overview_snapshot_drift_mismatching_snapshot_count": 1,
        "readiness_next_phase_candidate": "Stay Phase 1",
        "readiness_execution_ready": False,
        "phase_gate_decision": "CONDITIONAL_GO_NEEDS_LIVE_WINDOW",
        "phase2_entry_allowed": False,
        "phase_gate_reason": "remain_in_phase1_until_live_evidence_gate_clears",
        "phase_gate_strict_validation_passed": True,
        "phase_gate_strict_validation_issue_count": 2,
        "phase_gate_checked_files": 7,
        "phase_gate_review_report_path": "data/reports/phase_gate_review.md",
        "dashboard_status": "ok",
        "timeline_latest_remediation_planner_status": "stalled",
        "timeline_latest_remediation_planner_next_best_command": (
            "uv run sis validate-artifacts --strict"
        ),
        "timeline_latest_remediation_planner_feedback_priority_reason": ("evaluation_failed"),
        "timeline_latest_remediation_execution_plan_status": "stalled",
        "timeline_latest_remediation_execution_plan_next_action_command": (
            "uv run sis diagnose-quotes"
        ),
        "timeline_latest_remediation_execution_plan_feedback_priority_reason": (
            "evaluation_failed"
        ),
        "timeline_latest_remediation_session_status": "ready_for_dry_run",
        "timeline_latest_remediation_session_next_pending_command": (
            "uv run sis monitoring-status"
        ),
        "timeline_latest_remediation_session_feedback_priority_reason": ("evaluation_failed"),
        "timeline_latest_remediation_checkpoint_status": "retry_pending",
        "timeline_latest_remediation_checkpoint_next_action_command": (
            "uv run sis phase-gate-review"
        ),
        "timeline_latest_remediation_checkpoint_feedback_priority_reason": ("evaluation_failed"),
        "timeline_latest_remediation_scoreboard_status": "retrying",
        "timeline_latest_remediation_scoreboard_next_action_command": (
            "uv run sis phase-gate-review"
        ),
        "timeline_latest_remediation_scoreboard_feedback_priority_reason": ("evaluation_failed"),
    }


def test_current_schedule_section_lines_preserve_exact_order() -> None:
    assert current_schedule_section_lines(_summary()) == [
        "## Current Schedule",
        "",
        "- run_type: paper",
        "- scheduled_for: 2026-05-24T12:30:00+00:00",
        "- command: uv run sis paper-step",
    ]


def test_current_daemon_context_section_lines_preserve_exact_order() -> None:
    assert current_daemon_context_section_lines(
        _summary(),
        {
            "command": "uv run sis paper-step",
            "state_store_path": "data/state/marketlens.sqlite",
        },
    ) == [
        "## Current Daemon Context",
        "",
        "- daemon_mode: paper",
        "- daemon_command: uv run sis paper-step",
        "- state_store_path: data/state/marketlens.sqlite",
        "- daemon_manifest_path: data/ops/daemon_manifest.json",
    ]


def test_current_status_section_lines_preserve_exact_order() -> None:
    assert current_status_section_lines(_summary()) == [
        "## Current Status",
        "",
        "- monitoring_status: ok",
        "- execution_overall_status: ok",
        "- execution_venue_count: 2",
        "- execution_comparison_all_registries_present: True",
        "- execution_diagnostics_status: degraded",
        "- execution_balance_gap_detected: True",
        "- execution_fills_gap_detected: False",
        "- execution_gap_history_entry_count: 4",
        "- execution_gap_history_latest_status: ok",
        "- execution_gap_history_latest_diagnostics_status: degraded",
        "- execution_state_comparison_entry_count: 5",
        "- execution_state_comparison_latest_status_match: False",
        "- execution_state_comparison_mismatching_count: 1",
        "- execution_snapshot_drift_entry_count: 3",
        "- execution_snapshot_drift_latest_status_match: True",
        "- execution_snapshot_drift_mismatching_snapshot_count: 1",
        "- execution_drift_overview_status: degraded",
        "- execution_drift_overview_diagnostics_alignment_match: False",
        "- execution_drift_overview_state_comparison_mismatching_count: 1",
        "- execution_drift_overview_snapshot_drift_mismatching_snapshot_count: 1",
        "- readiness_next_phase_candidate: Stay Phase 1",
        "- readiness_execution_ready: False",
        "- phase_gate_decision: CONDITIONAL_GO_NEEDS_LIVE_WINDOW",
        "- phase2_entry_allowed: False",
        "- phase_gate_reason: remain_in_phase1_until_live_evidence_gate_clears",
        "- phase_gate_strict_validation_passed: True",
        "- phase_gate_strict_validation_issue_count: 2",
        "- phase_gate_checked_files: 7",
        "- phase_gate_review_report_path: data/reports/phase_gate_review.md",
        "- dashboard_status: ok",
    ]


def test_current_remediation_queue_section_lines_preserve_exact_order() -> None:
    assert current_remediation_queue_section_lines(_summary()) == [
        "## Current Remediation Queue",
        "",
        "- timeline_latest_remediation_planner_status: stalled",
        (
            "- timeline_latest_remediation_planner_next_best_command: "
            "uv run sis validate-artifacts --strict"
        ),
        "- timeline_latest_remediation_planner_feedback_priority_reason: evaluation_failed",
        "- timeline_latest_remediation_execution_plan_status: stalled",
        (
            "- timeline_latest_remediation_execution_plan_next_action_command: "
            "uv run sis diagnose-quotes"
        ),
        (
            "- timeline_latest_remediation_execution_plan_feedback_priority_reason: "
            "evaluation_failed"
        ),
        "- timeline_latest_remediation_session_status: ready_for_dry_run",
        (
            "- timeline_latest_remediation_session_next_pending_command: "
            "uv run sis monitoring-status"
        ),
        "- timeline_latest_remediation_session_feedback_priority_reason: evaluation_failed",
        "- timeline_latest_remediation_checkpoint_status: retry_pending",
        (
            "- timeline_latest_remediation_checkpoint_next_action_command: "
            "uv run sis phase-gate-review"
        ),
        ("- timeline_latest_remediation_checkpoint_feedback_priority_reason: evaluation_failed"),
        "- timeline_latest_remediation_scoreboard_status: retrying",
        (
            "- timeline_latest_remediation_scoreboard_next_action_command: "
            "uv run sis phase-gate-review"
        ),
        ("- timeline_latest_remediation_scoreboard_feedback_priority_reason: evaluation_failed"),
    ]
