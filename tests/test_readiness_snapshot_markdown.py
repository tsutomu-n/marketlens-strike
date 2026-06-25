from sis.reports.readiness_snapshot_markdown import render_readiness_snapshot_markdown


def _readiness_summary() -> dict[str, object]:
    return {
        "overall_status": "ok",
        "next_phase_candidate": "Phase 2",
        "phase_gate_decision": "GO",
        "phase2_entry_allowed": True,
        "phase2_entry_reason": "decision_cleared_and_phase1_gate_complete",
        "phase_gate_reason": "decision_cleared_and_phase1_gate_complete",
        "phase_gate_strict_validation_passed": True,
        "phase_gate_strict_validation_issue_count": 0,
        "phase_gate_checked_files": 7,
        "phase_gate_review_report_path": "data/reports/phase_gate_review.md",
        "phase_gate_strict_validation_issues": [],
        "execution_ready": True,
        "backtest_ready": True,
        "live_evidence_ready": True,
        "operations_ready": True,
        "research_quality_report_exists": True,
        "execution_balance_status_venue": "trade_xyz",
        "execution_balance_status_equity": 1500.0,
        "execution_fill_status_latest_fill_id": "fill-1",
        "execution_fill_status_latest_fill_symbol": "QQQ",
        "execution_order_status_status": "working",
        "execution_reconcile_positions_matched": 1,
        "execution_read_only_surfaces_venue_count": 2,
        "execution_read_only_surfaces_positions_notional_usd_total": 5000.0,
        "execution_read_only_surfaces_report_path": "data/reports/execution_read_only_surfaces.md",
        "daemon_manifest_mode": "paper",
        "daemon_loop_status": "completed",
        "daemon_loop_cycles_completed": 1,
        "daemon_loop_latest_event_status": "completed",
        "daemon_loop_report_path": "data/reports/daemon_loop.md",
        "notification_outbox_status": "queued",
        "notification_outbox_sink": "local_outbox",
        "notification_outbox_level": "warn",
        "notification_outbox_report_path": "data/reports/notification_outbox.md",
        "state_export_snapshot_path": "data/state/snapshot.json",
        "state_export_audit_overall_status": "ok",
        "state_export_phase_gate_decision": "GO",
        "state_export_readiness_next_phase_candidate": "Phase 2",
        "state_restore_restored": True,
        "state_restore_snapshot_path": "data/state/snapshot.json",
        "state_restore_audit_overall_status": "ok",
        "state_restore_phase_gate_decision": "GO",
        "restart_pointers": {
            "readiness_snapshot_report": "data/reports/readiness_snapshot.md",
            "current_state_index_report": "data/reports/current_state_index.md",
            "remediation_scoreboard_report": "data/reports/remediation_scoreboard.md",
        },
        "quick_navigation": {
            "phase_gate_review_report": "data/reports/phase_gate_review.md",
        },
        "related_reports": {
            "phase_gate_review_report": "data/reports/phase_gate_review.md",
        },
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
        "timeline_latest_remediation_checkpoint_next_action_command": "uv run sis phase-gate-review",
        "timeline_latest_remediation_checkpoint_feedback_priority_reason": "evaluation_failed",
        "timeline_latest_remediation_scoreboard_status": "retrying",
        "timeline_latest_remediation_scoreboard_next_action_command": "uv run sis phase-gate-review",
        "timeline_latest_remediation_scoreboard_feedback_priority_reason": "evaluation_failed",
        "execution_overall_status": "ok",
        "execution_venue_count": 2,
        "execution_comparison_all_registries_present": True,
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
        "live_evidence_status": "completed",
        "live_evidence_decision": "GO",
        "live_evidence_report_path": None,
        "operations_overall_status": "ok",
        "artifacts": {
            "current_state_index": "data/ops/current_state_index.json",
            "operations_dashboard_summary": "data/ops/operations_dashboard_summary.json",
        },
        "recommended_read_order": [
            "docs/CURRENT_STATE.md",
            "data/ops/readiness_snapshot.json",
        ],
    }


def test_render_readiness_snapshot_markdown_includes_core_sections() -> None:
    text = render_readiness_snapshot_markdown(_readiness_summary())

    assert "# Readiness Snapshot" in text
    assert "## Overall" in text
    assert "next_phase_candidate: Phase 2" in text
    assert "## Phase Gate" in text
    assert "phase_gate_decision: GO" in text
    assert "phase_gate_strict_validation_passed: True" in text
    assert "## Strict Validation Preview" in text
    assert "- issues: none" in text
    assert "## Readiness Flags" in text
    assert "execution_ready: True" in text
    assert "live_evidence_ready: True" in text
    assert "## Execution Adapter Surfaces" in text
    assert "execution_balance_status_equity: 1500.0" in text
    assert "execution_fill_status_latest_fill_id: fill-1" in text
    assert "execution_read_only_surfaces_positions_notional_usd_total: 5000.0" in text
    assert "## State And Daemon Surfaces" in text
    assert "daemon_loop_status: completed" in text
    assert "state_restore_restored: True" in text
    assert "## Restart Pointers" in text
    assert "- readiness_snapshot_report: data/reports/readiness_snapshot.md" in text
    assert "## Quick Navigation" in text
    assert "- phase_gate_review_report: data/reports/phase_gate_review.md" in text
    assert "## Latest Execution Lineage" in text
    assert "bundle_history_latest_execution_overall_status: warn" in text
    assert "## Current Remediation Queue" in text
    assert (
        "timeline_latest_remediation_session_next_pending_command: uv run sis monitoring-status"
        in text
    )
    assert "## Current State Metrics" in text
    assert "execution_gap_history_entry_count: 4" in text
    assert "live_evidence_report_path: None" in text
    assert "## Artifact Paths" in text
    assert "- current_state_index: data/ops/current_state_index.json" in text
    assert "## Recommended Read Order" in text
    assert "- docs/CURRENT_STATE.md" in text
