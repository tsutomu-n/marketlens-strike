from sis.reports.current_state_index_markdown import render_current_state_index_markdown


def _current_state_summary() -> dict[str, object]:
    return {
        "overall_status": "ok",
        "phase_gate_decision": "CONDITIONAL_GO_NEEDS_LIVE_WINDOW",
        "phase2_entry_allowed": False,
        "phase_gate_reason": "remain_in_phase1_until_live_evidence_gate_clears",
        "phase_gate_strict_validation_passed": True,
        "phase_gate_strict_validation_issue_count": 1,
        "phase_gate_checked_files": 7,
        "phase_gate_review_report_path": "data/reports/phase_gate_review.md",
        "phase_gate_strict_validation_issues": [
            {"path": "data/research/backtest_metrics_summary.json", "message": "missing field"}
        ],
        "audit_overall_status": "ok",
        "audit_latest_operation": "audit_bundle_snapshot",
        "timeline_latest_execution_overall_status": "ok",
        "timeline_latest_execution_venue_count": 2,
        "timeline_latest_execution_comparison_all_registries_present": True,
        "bundle_history_latest_execution_overall_status": "ok",
        "bundle_history_latest_execution_venue_count": 2,
        "bundle_history_latest_execution_comparison_all_registries_present": True,
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
        "state_export_phase_gate_decision": "CONDITIONAL_GO_NEEDS_LIVE_WINDOW",
        "state_export_readiness_next_phase_candidate": "Stay Phase 1",
        "state_restore_restored": True,
        "state_restore_snapshot_path": "data/state/snapshot.json",
        "state_restore_audit_overall_status": "ok",
        "state_restore_phase_gate_decision": "CONDITIONAL_GO_NEEDS_LIVE_WINDOW",
        "live_evidence_status": "completed",
        "live_evidence_decision": "GO",
        "live_evidence_run_id": "20260522_2308",
        "live_evidence_report_path": (
            "docs/live_evidence_reports/live_evidence_report_20260522_2308.md"
        ),
        "operations_cycle_count": 2,
        "quick_navigation": {
            "phase_gate_review_report": "data/reports/phase_gate_review.md",
        },
        "related_reports": {
            "current_state_index_report": "data/reports/current_state_index.md",
            "live_evidence_report": (
                "docs/live_evidence_reports/live_evidence_report_20260522_2308.md"
            ),
        },
        "restart_pointers": {
            "current_state_index_report": "data/reports/current_state_index.md",
            "readiness_snapshot_report": "data/reports/readiness_snapshot.md",
        },
        "artifacts": {
            "operations_dashboard_summary": "data/ops/operations_dashboard_summary.json",
            "live_evidence_report": (
                "docs/live_evidence_reports/live_evidence_report_20260522_2308.md"
            ),
        },
        "recommended_read_order": [
            "docs/CURRENT_STATE.md",
            "data/ops/current_state_index.json",
        ],
    }


def test_render_current_state_index_markdown_includes_core_sections() -> None:
    text = render_current_state_index_markdown(_current_state_summary())

    assert "# Current State Index" in text
    assert "## Overview" in text
    assert "phase_gate_decision: CONDITIONAL_GO_NEEDS_LIVE_WINDOW" in text
    assert "phase_gate_strict_validation_issue_count: 1" in text
    assert "timeline_latest_execution_overall_status: ok" in text
    assert "## Strict Validation Preview" in text
    assert "- data/research/backtest_metrics_summary.json: missing field" in text
    assert "## Research And Backtest" in text
    assert "execution_comparison_ready: True" in text
    assert "backtest_symbols: ['QQQ', 'SPY']" in text
    assert "## Execution Adapter Surfaces" in text
    assert "execution_balance_status_equity: 1500.0" in text
    assert "execution_read_only_surfaces_positions_notional_usd_total: 5000.0" in text
    assert "## State And Daemon Surfaces" in text
    assert "daemon_loop_status: completed" in text
    assert "state_restore_restored: True" in text
    assert "## Live Evidence" in text
    assert "live_evidence_run_id: 20260522_2308" in text
    assert "## Quick Navigation" in text
    assert "- phase_gate_review_report: data/reports/phase_gate_review.md" in text
    assert "## Related Reports" in text
    assert "## Restart Pointers" in text
    assert "- readiness_snapshot_report: data/reports/readiness_snapshot.md" in text
    assert "## Artifact Paths" in text
    assert "- operations_dashboard_summary: data/ops/operations_dashboard_summary.json" in text
    assert "## Recommended Read Order" in text
    assert "- docs/CURRENT_STATE.md" in text
