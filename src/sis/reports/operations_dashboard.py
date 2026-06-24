from __future__ import annotations

from pathlib import Path

from sis.reports.doc_paths import recommended_read_order
from sis.reports.loaders import normalized_summary, safe_read_json_dict
from sis.reports import operations_dashboard_navigation
from sis.reports.operations_dashboard_markdown import render_operations_dashboard_markdown
from sis.reports.summary_normalizers import (
    audit_summary_fields,
    audit_bundle_history_flat_fields,
    audit_bundle_flat_fields,
    audit_dashboard_flat_fields,
    audit_timeline_flat_fields,
    execution_comparison_flat_fields,
    execution_diagnostics_flat_fields,
    execution_gap_history_flat_fields,
    execution_snapshot_flat_fields,
    execution_snapshot_drift_flat_fields,
    execution_state_comparison_flat_fields,
    execution_drift_overview_flat_fields,
    normalize_execution_comparison_summary,
    normalize_execution_diagnostics_summary,
    normalize_execution_gap_history_summary,
    normalize_execution_snapshot_drift_summary,
    normalize_execution_snapshot_summary,
    normalize_execution_state_comparison_summary,
    normalize_execution_drift_overview_summary,
    ops_review_flat_fields,
    normalize_phase_gate_summary,
    merged_latest_execution_lineage_fields,
    phase_gate_flat_fields,
)
from sis.storage.jsonl_store import write_json


_report_path_for_summary = operations_dashboard_navigation.report_path_for_summary
_quick_navigation = operations_dashboard_navigation.quick_navigation
_related_reports = operations_dashboard_navigation.related_reports


def _execution_adapter_fields(
    source: dict[str, object], *, prefix: str, mapping: dict[str, str]
) -> dict[str, object]:
    if not isinstance(source, dict):
        return {}
    return {f"{prefix}_{target}": source.get(source_key) for target, source_key in mapping.items()}


def build_operations_dashboard(
    *,
    monitoring_snapshot_path: Path | None = None,
    ops_review_summary_path: Path | None = None,
    operations_timeline_summary_path: Path | None = None,
    decision_summary_path: Path | None = None,
    execution_snapshot_summary_path: Path | None = None,
    execution_venue_comparison_summary_path: Path | None = None,
    execution_venue_diagnostics_summary_path: Path | None = None,
    execution_gap_history_summary_path: Path | None = None,
    execution_state_comparison_history_summary_path: Path | None = None,
    execution_snapshot_drift_history_summary_path: Path | None = None,
    execution_drift_overview_summary_path: Path | None = None,
    execution_balance_status_summary_path: Path | None = None,
    execution_fill_status_summary_path: Path | None = None,
    execution_order_status_summary_path: Path | None = None,
    execution_cancel_order_summary_path: Path | None = None,
    execution_close_position_summary_path: Path | None = None,
    execution_reconcile_positions_summary_path: Path | None = None,
    execution_read_only_surfaces_summary_path: Path | None = None,
    daemon_manifest_summary_path: Path | None = None,
    daemon_loop_summary_path: Path | None = None,
    notification_outbox_summary_path: Path | None = None,
    state_export_summary_path: Path | None = None,
    state_restore_summary_path: Path | None = None,
    audit_dashboard_summary_path: Path | None = None,
    audit_bundle_summary_path: Path | None = None,
    operations_bundle_manifest_path: Path | None = None,
    phase_gate_summary_path: Path | None = None,
    comparison_report_path: Path | None = None,
    weekly_review_path: Path | None = None,
    lifecycle_report_path: Path | None = None,
    out_path: Path | None = None,
    summary_path: Path | None = None,
) -> str:
    monitoring = safe_read_json_dict(monitoring_snapshot_path)
    ops_review = safe_read_json_dict(ops_review_summary_path)
    operations_timeline = safe_read_json_dict(operations_timeline_summary_path)
    decision_summary = safe_read_json_dict(decision_summary_path)
    execution_snapshot = normalized_summary(
        execution_snapshot_summary_path,
        normalize_execution_snapshot_summary,
    )
    execution_comparison = normalized_summary(
        execution_venue_comparison_summary_path,
        normalize_execution_comparison_summary,
    )
    execution_diagnostics = normalized_summary(
        execution_venue_diagnostics_summary_path,
        normalize_execution_diagnostics_summary,
    )
    execution_gap_history = normalized_summary(
        execution_gap_history_summary_path,
        normalize_execution_gap_history_summary,
    )
    execution_state_comparison = normalized_summary(
        execution_state_comparison_history_summary_path,
        normalize_execution_state_comparison_summary,
    )
    execution_snapshot_drift = normalized_summary(
        execution_snapshot_drift_history_summary_path,
        normalize_execution_snapshot_drift_summary,
    )
    execution_drift_overview = normalized_summary(
        execution_drift_overview_summary_path,
        normalize_execution_drift_overview_summary,
    )
    execution_balance_status = safe_read_json_dict(execution_balance_status_summary_path)
    execution_fill_status = safe_read_json_dict(execution_fill_status_summary_path)
    execution_order_status = safe_read_json_dict(execution_order_status_summary_path)
    execution_cancel_order = safe_read_json_dict(execution_cancel_order_summary_path)
    execution_close_position = safe_read_json_dict(execution_close_position_summary_path)
    execution_reconcile_positions = safe_read_json_dict(execution_reconcile_positions_summary_path)
    execution_read_only_surfaces = safe_read_json_dict(execution_read_only_surfaces_summary_path)
    daemon_manifest = safe_read_json_dict(daemon_manifest_summary_path)
    daemon_loop = safe_read_json_dict(daemon_loop_summary_path)
    notification_outbox = safe_read_json_dict(notification_outbox_summary_path)
    state_export = safe_read_json_dict(state_export_summary_path)
    state_restore = safe_read_json_dict(state_restore_summary_path)
    audit_dashboard = safe_read_json_dict(audit_dashboard_summary_path)
    audit_bundle = safe_read_json_dict(audit_bundle_summary_path)
    operations_bundle = safe_read_json_dict(operations_bundle_manifest_path)
    phase_gate = normalized_summary(phase_gate_summary_path, normalize_phase_gate_summary)
    execution_snapshot_fields = execution_snapshot_flat_fields(execution_snapshot)
    execution_comparison_fields = execution_comparison_flat_fields(execution_comparison)
    execution_diagnostics_fields = execution_diagnostics_flat_fields(execution_diagnostics)
    execution_gap_history_fields = execution_gap_history_flat_fields(execution_gap_history)
    execution_state_comparison_fields = execution_state_comparison_flat_fields(
        execution_state_comparison
    )
    execution_snapshot_drift_fields = execution_snapshot_drift_flat_fields(execution_snapshot_drift)
    execution_drift_fields = execution_drift_overview_flat_fields(execution_drift_overview)
    execution_balance_fields = _execution_adapter_fields(
        execution_balance_status,
        prefix="execution_balance_status",
        mapping={
            "venue": "venue",
            "currency": "currency",
            "equity": "equity",
            "available_cash": "available_cash",
            "margin_used": "margin_used",
            "notional_usd": "notional_usd",
            "unrealized_pnl": "unrealized_pnl",
            "cumulative_rollover_usd": "cumulative_rollover_usd",
            "snapshot_exists": "balance_snapshot_exists",
            "report_path": "balance_status_report_path",
        },
    )
    execution_fill_fields = _execution_adapter_fields(
        execution_fill_status,
        prefix="execution_fill_status",
        mapping={
            "venue": "venue",
            "fills_count": "fills_count",
            "latest_fill_id": "latest_fill_id",
            "latest_fill_order_id": "latest_fill_order_id",
            "latest_fill_symbol": "latest_fill_symbol",
            "latest_fill_side": "latest_fill_side",
            "latest_fill_quantity": "latest_fill_quantity",
            "latest_fill_price": "latest_fill_price",
            "latest_fill_status": "latest_fill_status",
            "latest_fill_ts_fill": "latest_fill_ts_fill",
            "report_path": "fill_status_report_path",
        },
    )
    execution_order_fields = _execution_adapter_fields(
        execution_order_status,
        prefix="execution_order_status",
        mapping={
            "venue": "venue",
            "order_id": "order_id",
            "status": "status",
            "symbol": "symbol",
            "side": "side",
            "quantity": "quantity",
            "report_path": "order_status_report_path",
        },
    )
    execution_cancel_fields = _execution_adapter_fields(
        execution_cancel_order,
        prefix="execution_cancel_order",
        mapping={
            "venue": "venue",
            "action": "action",
            "target": "target",
            "success": "success",
            "status": "status",
            "report_path": "cancel_order_report_path",
        },
    )
    execution_close_fields = _execution_adapter_fields(
        execution_close_position,
        prefix="execution_close_position",
        mapping={
            "venue": "venue",
            "action": "action",
            "target": "target",
            "success": "success",
            "status": "status",
            "report_path": "close_position_report_path",
        },
    )
    execution_reconcile_fields = _execution_adapter_fields(
        execution_reconcile_positions,
        prefix="execution_reconcile_positions",
        mapping={
            "venue": "venue",
            "run_id": "run_id",
            "matched": "matched",
            "missing_in_adapter_count": "missing_in_adapter_count",
            "missing_in_internal_count": "missing_in_internal_count",
            "report_path": "reconcile_positions_report_path",
        },
    )
    execution_read_only_surface_fields = {
        "execution_read_only_surfaces_venue_count": execution_read_only_surfaces.get("venue_count"),
        "execution_read_only_surfaces_with_balance_snapshot_count": execution_read_only_surfaces.get(
            "with_balance_snapshot_count"
        ),
        "execution_read_only_surfaces_with_positions_snapshot_count": execution_read_only_surfaces.get(
            "with_positions_snapshot_count"
        ),
        "execution_read_only_surfaces_with_fills_snapshot_count": execution_read_only_surfaces.get(
            "with_fills_snapshot_count"
        ),
        "execution_read_only_surfaces_with_order_status_snapshot_count": execution_read_only_surfaces.get(
            "with_order_status_snapshot_count"
        ),
        "execution_read_only_surfaces_reconciled_venue_count": execution_read_only_surfaces.get(
            "reconciled_venue_count"
        ),
        "execution_read_only_surfaces_with_positions_financial_totals_count": execution_read_only_surfaces.get(
            "with_positions_financial_totals_count"
        ),
        "execution_read_only_surfaces_with_positions_rollover_metrics_count": execution_read_only_surfaces.get(
            "with_positions_rollover_metrics_count"
        ),
        "execution_read_only_surfaces_with_positions_protection_metrics_count": execution_read_only_surfaces.get(
            "with_positions_protection_metrics_count"
        ),
        "execution_read_only_surfaces_with_positions_leverage_metrics_count": execution_read_only_surfaces.get(
            "with_positions_leverage_metrics_count"
        ),
        "execution_read_only_surfaces_with_positions_return_metrics_count": execution_read_only_surfaces.get(
            "with_positions_return_metrics_count"
        ),
        "execution_read_only_surfaces_with_positions_day_trade_metrics_count": execution_read_only_surfaces.get(
            "with_positions_day_trade_metrics_count"
        ),
        "execution_read_only_surfaces_with_positions_limit_metrics_count": execution_read_only_surfaces.get(
            "with_positions_limit_metrics_count"
        ),
        "execution_read_only_surfaces_with_positions_quantity_metrics_count": execution_read_only_surfaces.get(
            "with_positions_quantity_metrics_count"
        ),
        "execution_read_only_surfaces_positions_notional_usd_total": execution_read_only_surfaces.get(
            "positions_notional_usd_total"
        ),
        "execution_read_only_surfaces_positions_unrealized_pnl_usd_total": execution_read_only_surfaces.get(
            "positions_unrealized_pnl_usd_total"
        ),
        "execution_read_only_surfaces_positions_collateral_used_usd_total": execution_read_only_surfaces.get(
            "positions_collateral_used_usd_total"
        ),
        "execution_read_only_surfaces_positions_max_withdrawable_usd_total": execution_read_only_surfaces.get(
            "positions_max_withdrawable_usd_total"
        ),
        "execution_read_only_surfaces_positions_cumulative_rollover_usd_total": execution_read_only_surfaces.get(
            "positions_cumulative_rollover_usd_total"
        ),
        "execution_read_only_surfaces_positions_with_liquidation_price_count": execution_read_only_surfaces.get(
            "positions_with_liquidation_price_count"
        ),
        "execution_read_only_surfaces_positions_with_take_profit_count": execution_read_only_surfaces.get(
            "positions_with_take_profit_count"
        ),
        "execution_read_only_surfaces_positions_with_stop_loss_count": execution_read_only_surfaces.get(
            "positions_with_stop_loss_count"
        ),
        "execution_read_only_surfaces_positions_day_trade_count": execution_read_only_surfaces.get(
            "positions_day_trade_count"
        ),
        "execution_read_only_surfaces_positions_average_leverage": execution_read_only_surfaces.get(
            "positions_average_leverage"
        ),
        "execution_read_only_surfaces_positions_average_return_on_equity": execution_read_only_surfaces.get(
            "positions_average_return_on_equity"
        ),
        "execution_read_only_surfaces_positions_max_leverage": execution_read_only_surfaces.get(
            "positions_max_leverage"
        ),
        "execution_read_only_surfaces_positions_total_quantity": execution_read_only_surfaces.get(
            "positions_total_quantity"
        ),
        "execution_read_only_surfaces_positions_total_realized_pnl": execution_read_only_surfaces.get(
            "positions_total_realized_pnl"
        ),
        "execution_read_only_surfaces_latest_positions_server_time_ms": execution_read_only_surfaces.get(
            "latest_positions_server_time_ms"
        ),
        "execution_read_only_surfaces_latest_positions_open_timestamp_ms": execution_read_only_surfaces.get(
            "latest_positions_open_timestamp_ms"
        ),
        "execution_read_only_surfaces_latest_positions_updated_at": execution_read_only_surfaces.get(
            "latest_positions_updated_at"
        ),
        "execution_read_only_surfaces_latest_positions_client_ts": execution_read_only_surfaces.get(
            "latest_positions_client_ts"
        ),
        "execution_read_only_surfaces_report_path": execution_read_only_surfaces.get(
            "execution_read_only_surfaces_report_path"
        ),
    }
    state_daemon_fields = {
        "daemon_manifest_mode": daemon_manifest.get("mode"),
        "daemon_manifest_command": daemon_manifest.get("command"),
        "daemon_manifest_state_store_path": daemon_manifest.get("state_store_path"),
        "daemon_manifest_report_path": daemon_manifest.get("daemon_manifest_report_path"),
        "daemon_loop_status": daemon_loop.get("status"),
        "daemon_loop_cycles_requested": daemon_loop.get("cycles_requested"),
        "daemon_loop_cycles_completed": daemon_loop.get("cycles_completed"),
        "daemon_loop_latest_event_status": daemon_loop.get("latest_event_status"),
        "daemon_loop_latest_event_exit_code": daemon_loop.get("latest_event_exit_code"),
        "daemon_loop_path": daemon_loop.get("daemon_loop_path"),
        "daemon_loop_events_path": daemon_loop.get("daemon_loop_events_path"),
        "daemon_loop_report_path": daemon_loop.get("daemon_loop_report_path"),
        "notification_outbox_status": notification_outbox.get("status"),
        "notification_outbox_sink": notification_outbox.get("sink"),
        "notification_outbox_level": notification_outbox.get("level"),
        "notification_outbox_title": notification_outbox.get("title"),
        "notification_outbox_source": notification_outbox.get("source"),
        "notification_outbox_path": notification_outbox.get("outbox_path"),
        "notification_outbox_latest_path": notification_outbox.get("latest_path"),
        "notification_outbox_report_path": notification_outbox.get(
            "notification_outbox_report_path"
        ),
        "state_export_snapshot_path": state_export.get("snapshot_path"),
        "state_export_audit_overall_status": state_export.get("audit_overall_status"),
        "state_export_phase_gate_decision": state_export.get("phase_gate_decision"),
        "state_export_readiness_next_phase_candidate": state_export.get(
            "readiness_next_phase_candidate"
        ),
        "state_export_report_path": state_export.get("state_export_report_path"),
        "state_restore_restored": state_restore.get("restored"),
        "state_restore_snapshot_path": state_restore.get("snapshot_path"),
        "state_restore_audit_overall_status": state_restore.get("audit_overall_status"),
        "state_restore_phase_gate_decision": state_restore.get("phase_gate_decision"),
        "state_restore_report_path": state_restore.get("state_restore_report_path"),
    }
    ops_review_fields = ops_review_flat_fields(ops_review)
    audit_dashboard_fields = audit_dashboard_flat_fields(audit_dashboard)
    audit_bundle_fields = audit_bundle_flat_fields(audit_bundle)
    audit_timeline_fields = audit_timeline_flat_fields(audit_dashboard)
    operations_timeline_fields = {
        key: value
        for key, value in audit_timeline_flat_fields(operations_timeline).items()
        if key.startswith("timeline_latest_remediation_")
    }
    audit_bundle_history_fields = audit_bundle_history_flat_fields(audit_bundle)
    audit_summary = audit_summary_fields(audit_dashboard, audit_bundle)
    latest_execution_lineage = merged_latest_execution_lineage_fields(
        audit_dashboard,
        audit_bundle,
        operations_bundle,
    )
    phase_gate_fields = phase_gate_flat_fields(phase_gate)

    comparison_exists = bool(comparison_report_path and comparison_report_path.exists())
    weekly_exists = bool(weekly_review_path and weekly_review_path.exists())
    lifecycle_exists = bool(lifecycle_report_path and lifecycle_report_path.exists())

    overall_status = "ok"
    if monitoring.get("status") == "degraded":
        overall_status = "degraded"
    if ops_review_fields.get("ops_latest_status") == "blocked":
        overall_status = "blocked"

    summary = {
        "overall_status": overall_status,
        "monitoring_status": monitoring.get("status"),
        "ops_latest_status": ops_review_fields.get("ops_latest_status"),
        "operations_count": ops_review_fields.get("ops_operations_count"),
        "decision_mode": decision_summary.get("mode"),
        "executed_count": decision_summary.get("executed_count"),
        "blocked_count": decision_summary.get("blocked_count"),
        "phase_gate_summary": phase_gate,
        "audit_summary": audit_summary,
        **latest_execution_lineage,
        "execution_summary": execution_snapshot,
        "execution_comparison_summary": execution_comparison,
        "execution_diagnostics_summary": execution_diagnostics,
        "execution_gap_history_summary": execution_gap_history,
        "execution_state_comparison_summary": execution_state_comparison,
        "execution_snapshot_drift_summary": execution_snapshot_drift,
        "execution_drift_overview_summary": execution_drift_overview,
        "execution_balance_status_summary": execution_balance_status,
        "execution_fill_status_summary": execution_fill_status,
        "execution_order_status_summary": execution_order_status,
        "execution_cancel_order_summary": execution_cancel_order,
        "execution_close_position_summary": execution_close_position,
        "execution_reconcile_positions_summary": execution_reconcile_positions,
        "execution_read_only_surfaces_summary": execution_read_only_surfaces,
        "daemon_manifest_summary": daemon_manifest,
        "daemon_loop_summary": daemon_loop,
        "notification_outbox_summary": notification_outbox,
        "state_export_summary": state_export,
        "state_restore_summary": state_restore,
        **execution_snapshot_fields,
        **execution_comparison_fields,
        **execution_diagnostics_fields,
        **execution_gap_history_fields,
        **execution_state_comparison_fields,
        **execution_snapshot_drift_fields,
        **execution_drift_fields,
        **execution_balance_fields,
        **execution_fill_fields,
        **execution_order_fields,
        **execution_cancel_fields,
        **execution_close_fields,
        **execution_reconcile_fields,
        **execution_read_only_surface_fields,
        **state_daemon_fields,
        **audit_dashboard_fields,
        **audit_bundle_fields,
        **audit_timeline_fields,
        **operations_timeline_fields,
        **audit_bundle_history_fields,
        **phase_gate_fields,
        "phase_gate_phase2_entry_allowed": phase_gate_fields.get("phase2_entry_allowed"),
        "phase_gate_summary_path": str(phase_gate_summary_path)
        if phase_gate_summary_path
        else None,
        "operations_dashboard_report_path": str(out_path) if out_path is not None else None,
        "comparison_report_exists": comparison_exists,
        "weekly_review_exists": weekly_exists,
        "lifecycle_report_exists": lifecycle_exists,
        "recommended_read_order": recommended_read_order(
            [
                "data/ops/execution_snapshot_summary.json",
                "data/ops/execution_venue_comparison_summary.json",
                "data/ops/execution_venue_diagnostics_summary.json",
                "data/ops/execution_gap_history_summary.json",
                "data/ops/execution_state_comparison_history_summary.json",
                "data/ops/execution_snapshot_drift_history_summary.json",
                "data/ops/execution_drift_overview_summary.json",
                "data/ops/execution_balance_status_summary.json",
                "data/ops/execution_fill_status_summary.json",
                "data/ops/execution_order_status_summary.json",
                "data/ops/execution_cancel_order_summary.json",
                "data/ops/execution_close_position_summary.json",
                "data/ops/execution_reconcile_positions_summary.json",
                "data/ops/execution_read_only_surfaces_summary.json",
                "data/ops/daemon_manifest_summary.json",
                "data/ops/daemon_loop_summary.json",
                "data/ops/notification_outbox_summary.json",
                "data/ops/state_export_summary.json",
                "data/ops/state_restore_summary.json",
                "data/ops/operations_dashboard_summary.json",
                "data/ops/audit_dashboard_summary.json",
                "data/ops/operations_bundle_manifest.json",
                "data/ops/audit_bundle_manifest.json",
            ]
        ),
    }
    quick_navigation = _quick_navigation(summary)
    related_reports = _related_reports(summary)
    recommended_read_order_items = recommended_read_order(
        [
            "data/ops/execution_snapshot_summary.json",
            "data/ops/execution_venue_comparison_summary.json",
            "data/ops/execution_venue_diagnostics_summary.json",
            "data/ops/execution_gap_history_summary.json",
            "data/ops/execution_state_comparison_history_summary.json",
            "data/ops/execution_snapshot_drift_history_summary.json",
            "data/ops/execution_drift_overview_summary.json",
            "data/ops/execution_balance_status_summary.json",
            "data/ops/execution_fill_status_summary.json",
            "data/ops/execution_order_status_summary.json",
            "data/ops/execution_cancel_order_summary.json",
            "data/ops/execution_close_position_summary.json",
            "data/ops/execution_reconcile_positions_summary.json",
            "data/ops/execution_read_only_surfaces_summary.json",
            "data/ops/daemon_manifest_summary.json",
            "data/ops/daemon_loop_summary.json",
            "data/ops/notification_outbox_summary.json",
            "data/ops/state_export_summary.json",
            "data/ops/state_restore_summary.json",
            "data/ops/operations_dashboard_summary.json",
            "data/ops/audit_dashboard_summary.json",
            "data/ops/operations_bundle_manifest.json",
            "data/ops/audit_bundle_manifest.json",
        ]
    )
    summary["quick_navigation"] = quick_navigation
    summary["related_reports"] = related_reports
    summary["recommended_read_order"] = recommended_read_order_items

    text = render_operations_dashboard_markdown(
        summary,
        monitoring=monitoring,
        ops_review_fields=ops_review_fields if ops_review else None,
    )
    if out_path is not None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text, encoding="utf-8")
    if summary_path is not None:
        write_json(summary_path, summary)
    return text
