from sis.reports.operations_dashboard_markdown import render_operations_dashboard_markdown


def _dashboard_summary() -> dict[str, object]:
    return {
        "overall_status": "blocked",
        "monitoring_status": "degraded",
        "ops_latest_status": "blocked",
        "operations_count": 3,
        "decision_mode": "signal_driven",
        "executed_count": 2,
        "blocked_count": 1,
        "execution_overall_status": "ok",
        "execution_venue_count": 2,
        "execution_comparison_all_registries_present": True,
        "execution_diagnostics_status": "degraded",
        "execution_balance_gap_detected": True,
        "execution_fills_gap_detected": False,
        "execution_gap_history_entry_count": 4,
        "execution_gap_history_latest_status": "ok",
        "execution_gap_history_latest_diagnostics_status": "degraded",
        "execution_state_comparison_entry_count": 4,
        "execution_state_comparison_latest_status_match": False,
        "execution_state_comparison_mismatching_count": 1,
        "execution_snapshot_drift_entry_count": 3,
        "execution_snapshot_drift_latest_status_match": True,
        "execution_snapshot_drift_mismatching_snapshot_count": 1,
        "execution_drift_overview_status": "degraded",
        "execution_drift_overview_diagnostics_alignment_match": False,
        "execution_drift_overview_state_comparison_mismatching_count": 1,
        "execution_drift_overview_snapshot_drift_mismatching_snapshot_count": 1,
        "execution_balance_status_venue": "trade_xyz",
        "execution_balance_status_currency": "USD",
        "execution_balance_status_equity": 1500.0,
        "execution_balance_status_available_cash": 1200.0,
        "execution_balance_status_margin_used": 300.0,
        "execution_balance_status_notional_usd": 5000.0,
        "execution_balance_status_unrealized_pnl": 25.0,
        "execution_balance_status_cumulative_rollover_usd": -1.5,
        "execution_fill_status_venue": "trade_xyz",
        "execution_fill_status_fills_count": 2,
        "execution_fill_status_latest_fill_id": "fill-1",
        "execution_fill_status_latest_fill_order_id": "order-1",
        "execution_fill_status_latest_fill_symbol": "QQQ",
        "execution_fill_status_latest_fill_side": "long",
        "execution_fill_status_latest_fill_quantity": 1,
        "execution_fill_status_latest_fill_price": 100.5,
        "execution_fill_status_latest_fill_status": "filled",
        "execution_fill_status_latest_fill_ts_fill": "2026-05-24T00:00:00+00:00",
        "execution_order_status_venue": "trade_xyz",
        "execution_order_status_order_id": "order-1",
        "execution_order_status_status": "working",
        "execution_order_status_symbol": "QQQ",
        "execution_order_status_side": "long",
        "execution_order_status_quantity": 1,
        "execution_cancel_order_target": "order-1",
        "execution_cancel_order_status": "blocked_read_only",
        "execution_close_position_target": "QQQ",
        "execution_close_position_status": "blocked_read_only",
        "execution_reconcile_positions_matched": 1,
        "execution_reconcile_positions_missing_in_adapter_count": 0,
        "execution_reconcile_positions_missing_in_internal_count": 0,
        "execution_read_only_surfaces_venue_count": 1,
        "execution_read_only_surfaces_with_balance_snapshot_count": 1,
        "execution_read_only_surfaces_with_positions_snapshot_count": 1,
        "execution_read_only_surfaces_with_fills_snapshot_count": 1,
        "execution_read_only_surfaces_with_order_status_snapshot_count": 1,
        "execution_read_only_surfaces_reconciled_venue_count": 1,
        "execution_read_only_surfaces_with_positions_financial_totals_count": 1,
        "execution_read_only_surfaces_with_positions_rollover_metrics_count": 1,
        "execution_read_only_surfaces_with_positions_protection_metrics_count": 1,
        "execution_read_only_surfaces_with_positions_leverage_metrics_count": 1,
        "execution_read_only_surfaces_with_positions_return_metrics_count": 1,
        "execution_read_only_surfaces_with_positions_day_trade_metrics_count": 1,
        "execution_read_only_surfaces_with_positions_limit_metrics_count": 1,
        "execution_read_only_surfaces_with_positions_quantity_metrics_count": 1,
        "execution_read_only_surfaces_positions_notional_usd_total": 5000.0,
        "execution_read_only_surfaces_positions_unrealized_pnl_usd_total": 25.0,
        "execution_read_only_surfaces_positions_collateral_used_usd_total": 300.0,
        "execution_read_only_surfaces_positions_max_withdrawable_usd_total": 1200.0,
        "execution_read_only_surfaces_positions_cumulative_rollover_usd_total": -1.5,
        "execution_read_only_surfaces_positions_with_liquidation_price_count": 1,
        "execution_read_only_surfaces_positions_with_take_profit_count": 1,
        "execution_read_only_surfaces_positions_with_stop_loss_count": 1,
        "execution_read_only_surfaces_positions_day_trade_count": 0,
        "execution_read_only_surfaces_positions_average_leverage": 2.0,
        "execution_read_only_surfaces_positions_average_return_on_equity": 0.05,
        "execution_read_only_surfaces_positions_max_leverage": 3.0,
        "execution_read_only_surfaces_positions_total_quantity": 1.0,
        "execution_read_only_surfaces_positions_total_realized_pnl": 0.0,
        "execution_read_only_surfaces_latest_positions_server_time_ms": 1779408000000,
        "execution_read_only_surfaces_latest_positions_open_timestamp_ms": 1779407000000,
        "execution_read_only_surfaces_latest_positions_updated_at": "2026-05-24T00:00:00+00:00",
        "execution_read_only_surfaces_latest_positions_client_ts": "2026-05-24T00:00:00+00:00",
        "execution_read_only_surfaces_report_path": "data/reports/execution_read_only_surfaces.md",
        "daemon_manifest_mode": "paper",
        "daemon_manifest_command": "uv run sis paper-step",
        "daemon_manifest_state_store_path": "data/state/state.json",
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
        "audit_overall_status": "ok",
        "audit_latest_operation": "audit_bundle_snapshot",
        "audit_entry_count": 5,
        "audit_bundle_snapshot_count": 3,
        "audit_bundle_history_snapshot_count": 3,
        "audit_bundle_history_ok_count": 3,
        "timeline_latest_execution_overall_status": "ok",
        "timeline_latest_execution_venue_count": 2,
        "timeline_latest_execution_comparison_all_registries_present": True,
        "timeline_latest_remediation_planner_status": "stalled",
        "timeline_latest_remediation_planner_next_best_command": "uv run sis validate-artifacts --strict",
        "timeline_latest_remediation_execution_plan_status": "stalled",
        "timeline_latest_remediation_execution_plan_next_action_command": "uv run sis diagnose-quotes",
        "timeline_latest_remediation_session_status": "ready_for_dry_run",
        "timeline_latest_remediation_session_next_pending_command": "uv run sis monitoring-status",
        "timeline_latest_remediation_checkpoint_status": "retry_pending",
        "timeline_latest_remediation_checkpoint_next_action_command": "uv run sis phase-gate-review",
        "timeline_latest_remediation_scoreboard_status": "retrying",
        "timeline_latest_remediation_scoreboard_next_action_command": "uv run sis phase-gate-review",
        "phase_gate_decision": "CONDITIONAL_GO_NEEDS_LIVE_WINDOW",
        "phase_gate_phase2_entry_allowed": False,
        "phase_gate_reason": "remain_in_phase1_until_live_evidence_gate_clears",
        "phase_gate_strict_validation_passed": True,
        "phase_gate_strict_validation_issue_count": 1,
        "phase_gate_checked_files": 7,
        "phase_gate_review_report_path": "data/reports/phase_gate_review.md",
        "phase_gate_strict_validation_issues": [
            {"path": "data/research/backtest_metrics_summary.json", "message": "missing field"}
        ],
        "comparison_report_exists": True,
        "weekly_review_exists": True,
        "lifecycle_report_exists": False,
        "quick_navigation": {
            "operations_dashboard_report": "data/reports/operations_dashboard.md",
            "phase_gate_review_report": "data/reports/phase_gate_review.md",
        },
        "related_reports": {
            "current_state_index_report": "data/reports/current_state_index.md",
        },
        "recommended_read_order": [
            "data/ops/execution_snapshot_summary.json",
            "data/ops/operations_dashboard_summary.json",
        ],
    }


def test_render_operations_dashboard_markdown_includes_core_sections() -> None:
    text = render_operations_dashboard_markdown(
        _dashboard_summary(),
        monitoring={
            "decision_summary_exists": True,
            "daily_pnl_exists": True,
            "operation_chain_exists": True,
        },
        ops_review_fields={
            "ops_latest_operation": "daemon_dry_run",
            "ops_latest_scheduled_for": "2026-05-24T12:30:00+00:00",
        },
    )

    assert "# Operations Dashboard" in text
    assert "overall_status: blocked" in text
    assert "## Quick Navigation" in text
    assert "- operations_dashboard_report: data/reports/operations_dashboard.md" in text
    assert "## Decision State" in text
    assert "execution_drift_overview_status: degraded" in text
    assert "## Execution Adapter Surfaces" in text
    assert "execution_balance_status_equity: 1500.0" in text
    assert "## State And Daemon Surfaces" in text
    assert "daemon_loop_status: completed" in text
    assert "## Phase Gate State" in text
    assert "phase_gate_decision: CONDITIONAL_GO_NEEDS_LIVE_WINDOW" in text
    assert "## Strict Validation Preview" in text
    assert "- data/research/backtest_metrics_summary.json: missing field" in text
    assert "## Recommended Read Order" in text
    assert "- data/ops/operations_dashboard_summary.json" in text
    assert "## Monitoring Hints" in text
    assert "decision_summary_exists: True" in text
    assert "## Ops Review Hints" in text
    assert "latest_operation: daemon_dry_run" in text
