from __future__ import annotations

from sis.reports.current_state_index_markdown_sections import (
    overview_section_lines,
    research_and_backtest_section_lines,
)


def _summary() -> dict[str, object]:
    return {
        "overall_status": "ok",
        "phase_gate_decision": "CONDITIONAL_GO_NEEDS_LIVE_WINDOW",
        "phase2_entry_allowed": False,
        "phase_gate_reason": "remain_in_phase1_until_live_evidence_gate_clears",
        "phase_gate_strict_validation_passed": True,
        "phase_gate_strict_validation_issue_count": 1,
        "phase_gate_checked_files": 7,
        "phase_gate_review_report_path": "data/reports/phase_gate_review.md",
        "audit_overall_status": "ok",
        "audit_latest_operation": "audit_bundle_snapshot",
        "timeline_latest_execution_overall_status": "ok",
        "timeline_latest_execution_venue_count": 2,
        "timeline_latest_execution_comparison_all_registries_present": True,
        "bundle_history_latest_execution_overall_status": "warn",
        "bundle_history_latest_execution_venue_count": 1,
        "bundle_history_latest_execution_comparison_all_registries_present": False,
        "cycle_history_latest_execution_overall_status": "ok",
        "cycle_history_latest_execution_venue_count": 2,
        "cycle_history_latest_execution_comparison_all_registries_present": True,
        "timeline_latest_remediation_planner_status": "stalled",
        "timeline_latest_remediation_planner_next_best_command": (
            "uv run sis validate-artifacts --strict"
        ),
        "timeline_latest_remediation_planner_feedback_priority_reason": "evaluation_failed",
        "timeline_latest_remediation_execution_plan_status": "stalled",
        "timeline_latest_remediation_execution_plan_next_action_command": (
            "uv run sis diagnose-quotes"
        ),
        "timeline_latest_remediation_execution_plan_feedback_priority_reason": "evaluation_failed",
        "timeline_latest_remediation_session_status": "ready_for_dry_run",
        "timeline_latest_remediation_session_next_pending_command": (
            "uv run sis monitoring-status"
        ),
        "timeline_latest_remediation_session_feedback_priority_reason": "evaluation_failed",
        "timeline_latest_remediation_checkpoint_status": "retry_pending",
        "timeline_latest_remediation_checkpoint_next_action_command": (
            "uv run sis phase-gate-review"
        ),
        "timeline_latest_remediation_checkpoint_feedback_priority_reason": "evaluation_failed",
        "timeline_latest_remediation_scoreboard_status": "retrying",
        "timeline_latest_remediation_scoreboard_next_action_command": (
            "uv run sis phase-gate-review"
        ),
        "timeline_latest_remediation_scoreboard_feedback_priority_reason": "evaluation_failed",
        "execution_overall_status": "ok",
        "execution_venue_count": 2,
        "execution_comparison_ready": True,
        "execution_diagnostics_status": "ok",
        "execution_balance_gap_detected": False,
        "execution_fills_gap_detected": False,
        "execution_gap_history_entry_count": 4,
        "execution_gap_history_latest_status": "ok",
        "execution_gap_history_latest_diagnostics_status": "ok",
        "execution_state_comparison_entry_count": 4,
        "execution_state_comparison_latest_status_match": True,
        "execution_state_comparison_mismatching_count": 0,
        "execution_snapshot_drift_entry_count": 3,
        "execution_snapshot_drift_latest_status_match": True,
        "execution_snapshot_drift_mismatching_snapshot_count": 0,
        "execution_drift_overview_status": "ok",
        "execution_drift_overview_diagnostics_alignment_match": True,
        "execution_drift_overview_state_comparison_mismatching_count": 0,
        "execution_drift_overview_snapshot_drift_mismatching_snapshot_count": 0,
        "backtest_total_trade_count": 5,
        "backtest_symbols": ["QQQ", "SPY"],
        "research_quality_report_exists": True,
    }


def test_overview_section_lines_preserve_exact_order() -> None:
    assert overview_section_lines(_summary()) == [
        "## Overview",
        "",
        "- overall_status: ok",
        "- phase_gate_decision: CONDITIONAL_GO_NEEDS_LIVE_WINDOW",
        "- phase2_entry_allowed: False",
        "- phase_gate_reason: remain_in_phase1_until_live_evidence_gate_clears",
        "- phase_gate_strict_validation_passed: True",
        "- phase_gate_strict_validation_issue_count: 1",
        "- phase_gate_checked_files: 7",
        "- phase_gate_review_report_path: data/reports/phase_gate_review.md",
        "- audit_overall_status: ok",
        "- audit_latest_operation: audit_bundle_snapshot",
        "- timeline_latest_execution_overall_status: ok",
        "- timeline_latest_execution_venue_count: 2",
        "- timeline_latest_execution_comparison_all_registries_present: True",
        "- bundle_history_latest_execution_overall_status: warn",
        "- bundle_history_latest_execution_venue_count: 1",
        "- bundle_history_latest_execution_comparison_all_registries_present: False",
        "- cycle_history_latest_execution_overall_status: ok",
        "- cycle_history_latest_execution_venue_count: 2",
        "- cycle_history_latest_execution_comparison_all_registries_present: True",
        "- timeline_latest_remediation_planner_status: stalled",
        (
            "- timeline_latest_remediation_planner_next_best_command: "
            "uv run sis validate-artifacts --strict"
        ),
        ("- timeline_latest_remediation_planner_feedback_priority_reason: evaluation_failed"),
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
        ("- timeline_latest_remediation_session_feedback_priority_reason: evaluation_failed"),
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


def test_research_and_backtest_section_lines_preserve_exact_order() -> None:
    assert research_and_backtest_section_lines(_summary()) == [
        "## Research And Backtest",
        "",
        "- execution_overall_status: ok",
        "- execution_venue_count: 2",
        "- execution_comparison_ready: True",
        "- execution_diagnostics_status: ok",
        "- execution_balance_gap_detected: False",
        "- execution_fills_gap_detected: False",
        "- execution_gap_history_entry_count: 4",
        "- execution_gap_history_latest_status: ok",
        "- execution_gap_history_latest_diagnostics_status: ok",
        "- execution_state_comparison_entry_count: 4",
        "- execution_state_comparison_latest_status_match: True",
        "- execution_state_comparison_mismatching_count: 0",
        "- execution_snapshot_drift_entry_count: 3",
        "- execution_snapshot_drift_latest_status_match: True",
        "- execution_snapshot_drift_mismatching_snapshot_count: 0",
        "- execution_drift_overview_status: ok",
        "- execution_drift_overview_diagnostics_alignment_match: True",
        "- execution_drift_overview_state_comparison_mismatching_count: 0",
        "- execution_drift_overview_snapshot_drift_mismatching_snapshot_count: 0",
        "- backtest_total_trade_count: 5",
        "- backtest_symbols: ['QQQ', 'SPY']",
        "- research_quality_report_exists: True",
    ]
