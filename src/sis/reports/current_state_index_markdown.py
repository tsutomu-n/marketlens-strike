from __future__ import annotations

from typing import Any, cast

from sis.reports.current_state_index_markdown_sections import (
    overview_section_lines,
    research_and_backtest_section_lines,
)
from sis.reports.summary_normalizers import (
    phase_gate_issue_preview_lines,
)


def render_current_state_index_markdown(summary: dict[str, Any]) -> str:
    quick_navigation = _dict(summary.get("quick_navigation"))
    related_reports = _dict(summary.get("related_reports"))
    restart_pointers = _dict(summary.get("restart_pointers"))
    artifacts = _dict(summary.get("artifacts"))
    recommended_read_order_items = _list(summary.get("recommended_read_order"))

    lines = [
        "# Current State Index",
        "",
        *overview_section_lines(summary),
        "",
        "## Strict Validation Preview",
        "",
    ]
    validation_issue_previews = phase_gate_issue_preview_lines(summary)
    if validation_issue_previews:
        lines.extend(f"- {item}" for item in validation_issue_previews)
    else:
        lines.append("- issues: none")
    lines.extend(["", *research_and_backtest_section_lines(summary)])
    lines.extend(["", "## Execution Adapter Surfaces", ""])
    lines.extend(
        [
            f"- execution_balance_status_venue: {summary.get('execution_balance_status_venue')}",
            f"- execution_balance_status_currency: {summary.get('execution_balance_status_currency')}",
            f"- execution_balance_status_equity: {summary.get('execution_balance_status_equity')}",
            f"- execution_balance_status_available_cash: {summary.get('execution_balance_status_available_cash')}",
            f"- execution_balance_status_margin_used: {summary.get('execution_balance_status_margin_used')}",
            f"- execution_balance_status_notional_usd: {summary.get('execution_balance_status_notional_usd')}",
            f"- execution_balance_status_unrealized_pnl: {summary.get('execution_balance_status_unrealized_pnl')}",
            f"- execution_balance_status_cumulative_rollover_usd: {summary.get('execution_balance_status_cumulative_rollover_usd')}",
            f"- execution_fill_status_venue: {summary.get('execution_fill_status_venue')}",
            f"- execution_fill_status_fills_count: {summary.get('execution_fill_status_fills_count')}",
            f"- execution_fill_status_latest_fill_id: {summary.get('execution_fill_status_latest_fill_id')}",
            f"- execution_fill_status_latest_fill_order_id: {summary.get('execution_fill_status_latest_fill_order_id')}",
            f"- execution_fill_status_latest_fill_symbol: {summary.get('execution_fill_status_latest_fill_symbol')}",
            f"- execution_fill_status_latest_fill_side: {summary.get('execution_fill_status_latest_fill_side')}",
            f"- execution_fill_status_latest_fill_quantity: {summary.get('execution_fill_status_latest_fill_quantity')}",
            f"- execution_fill_status_latest_fill_price: {summary.get('execution_fill_status_latest_fill_price')}",
            f"- execution_fill_status_latest_fill_status: {summary.get('execution_fill_status_latest_fill_status')}",
            f"- execution_fill_status_latest_fill_ts_fill: {summary.get('execution_fill_status_latest_fill_ts_fill')}",
            f"- execution_order_status_venue: {summary.get('execution_order_status_venue')}",
            f"- execution_order_status_order_id: {summary.get('execution_order_status_order_id')}",
            f"- execution_order_status_status: {summary.get('execution_order_status_status')}",
            f"- execution_order_status_symbol: {summary.get('execution_order_status_symbol')}",
            f"- execution_order_status_side: {summary.get('execution_order_status_side')}",
            f"- execution_order_status_quantity: {summary.get('execution_order_status_quantity')}",
            f"- execution_cancel_order_target: {summary.get('execution_cancel_order_target')}",
            f"- execution_cancel_order_status: {summary.get('execution_cancel_order_status')}",
            f"- execution_close_position_target: {summary.get('execution_close_position_target')}",
            f"- execution_close_position_status: {summary.get('execution_close_position_status')}",
            f"- execution_reconcile_positions_matched: {summary.get('execution_reconcile_positions_matched')}",
            (
                "- execution_reconcile_positions_missing_in_adapter_count: "
                f"{summary.get('execution_reconcile_positions_missing_in_adapter_count')}"
            ),
            (
                "- execution_reconcile_positions_missing_in_internal_count: "
                f"{summary.get('execution_reconcile_positions_missing_in_internal_count')}"
            ),
            f"- execution_read_only_surfaces_venue_count: {summary.get('execution_read_only_surfaces_venue_count')}",
            (
                "- execution_read_only_surfaces_with_balance_snapshot_count: "
                f"{summary.get('execution_read_only_surfaces_with_balance_snapshot_count')}"
            ),
            (
                "- execution_read_only_surfaces_with_positions_snapshot_count: "
                f"{summary.get('execution_read_only_surfaces_with_positions_snapshot_count')}"
            ),
            (
                "- execution_read_only_surfaces_with_fills_snapshot_count: "
                f"{summary.get('execution_read_only_surfaces_with_fills_snapshot_count')}"
            ),
            (
                "- execution_read_only_surfaces_with_order_status_snapshot_count: "
                f"{summary.get('execution_read_only_surfaces_with_order_status_snapshot_count')}"
            ),
            (
                "- execution_read_only_surfaces_reconciled_venue_count: "
                f"{summary.get('execution_read_only_surfaces_reconciled_venue_count')}"
            ),
            (
                "- execution_read_only_surfaces_with_positions_financial_totals_count: "
                f"{summary.get('execution_read_only_surfaces_with_positions_financial_totals_count')}"
            ),
            (
                "- execution_read_only_surfaces_with_positions_rollover_metrics_count: "
                f"{summary.get('execution_read_only_surfaces_with_positions_rollover_metrics_count')}"
            ),
            (
                "- execution_read_only_surfaces_with_positions_protection_metrics_count: "
                f"{summary.get('execution_read_only_surfaces_with_positions_protection_metrics_count')}"
            ),
            (
                "- execution_read_only_surfaces_with_positions_leverage_metrics_count: "
                f"{summary.get('execution_read_only_surfaces_with_positions_leverage_metrics_count')}"
            ),
            (
                "- execution_read_only_surfaces_with_positions_return_metrics_count: "
                f"{summary.get('execution_read_only_surfaces_with_positions_return_metrics_count')}"
            ),
            (
                "- execution_read_only_surfaces_with_positions_day_trade_metrics_count: "
                f"{summary.get('execution_read_only_surfaces_with_positions_day_trade_metrics_count')}"
            ),
            (
                "- execution_read_only_surfaces_with_positions_limit_metrics_count: "
                f"{summary.get('execution_read_only_surfaces_with_positions_limit_metrics_count')}"
            ),
            (
                "- execution_read_only_surfaces_with_positions_quantity_metrics_count: "
                f"{summary.get('execution_read_only_surfaces_with_positions_quantity_metrics_count')}"
            ),
            (
                "- execution_read_only_surfaces_positions_notional_usd_total: "
                f"{summary.get('execution_read_only_surfaces_positions_notional_usd_total')}"
            ),
            (
                "- execution_read_only_surfaces_positions_unrealized_pnl_usd_total: "
                f"{summary.get('execution_read_only_surfaces_positions_unrealized_pnl_usd_total')}"
            ),
            (
                "- execution_read_only_surfaces_positions_collateral_used_usd_total: "
                f"{summary.get('execution_read_only_surfaces_positions_collateral_used_usd_total')}"
            ),
            (
                "- execution_read_only_surfaces_positions_max_withdrawable_usd_total: "
                f"{summary.get('execution_read_only_surfaces_positions_max_withdrawable_usd_total')}"
            ),
            (
                "- execution_read_only_surfaces_positions_cumulative_rollover_usd_total: "
                f"{summary.get('execution_read_only_surfaces_positions_cumulative_rollover_usd_total')}"
            ),
            (
                "- execution_read_only_surfaces_positions_with_liquidation_price_count: "
                f"{summary.get('execution_read_only_surfaces_positions_with_liquidation_price_count')}"
            ),
            (
                "- execution_read_only_surfaces_positions_with_take_profit_count: "
                f"{summary.get('execution_read_only_surfaces_positions_with_take_profit_count')}"
            ),
            (
                "- execution_read_only_surfaces_positions_with_stop_loss_count: "
                f"{summary.get('execution_read_only_surfaces_positions_with_stop_loss_count')}"
            ),
            (
                "- execution_read_only_surfaces_positions_day_trade_count: "
                f"{summary.get('execution_read_only_surfaces_positions_day_trade_count')}"
            ),
            (
                "- execution_read_only_surfaces_positions_average_leverage: "
                f"{summary.get('execution_read_only_surfaces_positions_average_leverage')}"
            ),
            (
                "- execution_read_only_surfaces_positions_average_return_on_equity: "
                f"{summary.get('execution_read_only_surfaces_positions_average_return_on_equity')}"
            ),
            (
                "- execution_read_only_surfaces_positions_max_leverage: "
                f"{summary.get('execution_read_only_surfaces_positions_max_leverage')}"
            ),
            (
                "- execution_read_only_surfaces_positions_total_quantity: "
                f"{summary.get('execution_read_only_surfaces_positions_total_quantity')}"
            ),
            (
                "- execution_read_only_surfaces_positions_total_realized_pnl: "
                f"{summary.get('execution_read_only_surfaces_positions_total_realized_pnl')}"
            ),
            (
                "- execution_read_only_surfaces_latest_positions_server_time_ms: "
                f"{summary.get('execution_read_only_surfaces_latest_positions_server_time_ms')}"
            ),
            (
                "- execution_read_only_surfaces_latest_positions_open_timestamp_ms: "
                f"{summary.get('execution_read_only_surfaces_latest_positions_open_timestamp_ms')}"
            ),
            (
                "- execution_read_only_surfaces_latest_positions_updated_at: "
                f"{summary.get('execution_read_only_surfaces_latest_positions_updated_at')}"
            ),
            (
                "- execution_read_only_surfaces_latest_positions_client_ts: "
                f"{summary.get('execution_read_only_surfaces_latest_positions_client_ts')}"
            ),
            f"- execution_read_only_surfaces_report_path: {summary.get('execution_read_only_surfaces_report_path')}",
        ]
    )
    lines.extend(["", "## State And Daemon Surfaces", ""])
    lines.extend(
        [
            f"- daemon_manifest_mode: {summary.get('daemon_manifest_mode')}",
            f"- daemon_manifest_command: {summary.get('daemon_manifest_command')}",
            f"- daemon_manifest_state_store_path: {summary.get('daemon_manifest_state_store_path')}",
            f"- daemon_loop_status: {summary.get('daemon_loop_status')}",
            f"- daemon_loop_cycles_completed: {summary.get('daemon_loop_cycles_completed')}",
            f"- daemon_loop_latest_event_status: {summary.get('daemon_loop_latest_event_status')}",
            f"- daemon_loop_report_path: {summary.get('daemon_loop_report_path')}",
            f"- notification_outbox_status: {summary.get('notification_outbox_status')}",
            f"- notification_outbox_sink: {summary.get('notification_outbox_sink')}",
            f"- notification_outbox_level: {summary.get('notification_outbox_level')}",
            f"- notification_outbox_report_path: {summary.get('notification_outbox_report_path')}",
            f"- state_export_snapshot_path: {summary.get('state_export_snapshot_path')}",
            f"- state_export_audit_overall_status: {summary.get('state_export_audit_overall_status')}",
            f"- state_export_phase_gate_decision: {summary.get('state_export_phase_gate_decision')}",
            (
                "- state_export_readiness_next_phase_candidate: "
                f"{summary.get('state_export_readiness_next_phase_candidate')}"
            ),
            f"- state_restore_restored: {summary.get('state_restore_restored')}",
            f"- state_restore_snapshot_path: {summary.get('state_restore_snapshot_path')}",
            f"- state_restore_audit_overall_status: {summary.get('state_restore_audit_overall_status')}",
            f"- state_restore_phase_gate_decision: {summary.get('state_restore_phase_gate_decision')}",
        ]
    )
    lines.extend(["", "## Live Evidence", ""])
    lines.extend(
        [
            f"- live_evidence_status: {summary['live_evidence_status']}",
            f"- live_evidence_decision: {summary['live_evidence_decision']}",
            f"- live_evidence_run_id: {summary['live_evidence_run_id']}",
            f"- live_evidence_report_path: {summary['live_evidence_report_path']}",
        ]
    )
    lines.extend(["", "## Operations", ""])
    lines.append(f"- operations_cycle_count: {summary['operations_cycle_count']}")
    lines.extend(["", "## Quick Navigation", ""])
    for key, value in quick_navigation.items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Related Reports", ""])
    for key, value in related_reports.items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Restart Pointers", ""])
    for key, value in restart_pointers.items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Artifact Paths", ""])
    for key, value in artifacts.items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Recommended Read Order", ""])
    lines.extend(f"- {item}" for item in recommended_read_order_items)
    lines.append("")

    return "\n".join(lines)


def _dict(value: object) -> dict[str, object]:
    if isinstance(value, dict):
        return cast(dict[str, object], value)
    return {}


def _list(value: object) -> list[object]:
    if isinstance(value, list):
        return cast(list[object], value)
    return []
