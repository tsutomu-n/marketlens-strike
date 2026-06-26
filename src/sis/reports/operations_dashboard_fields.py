from __future__ import annotations

from collections.abc import Mapping
from typing import cast


def execution_adapter_fields(
    source: object, *, prefix: str, mapping: Mapping[str, str]
) -> dict[str, object]:
    if not isinstance(source, Mapping):
        return {}
    source_mapping = cast(Mapping[str, object], source)
    return {
        f"{prefix}_{target}": source_mapping.get(source_key)
        for target, source_key in mapping.items()
    }


READ_ONLY_SURFACE_FIELD_MAPPING = (
    ("execution_read_only_surfaces_venue_count", "venue_count"),
    ("execution_read_only_surfaces_with_balance_snapshot_count", "with_balance_snapshot_count"),
    ("execution_read_only_surfaces_with_positions_snapshot_count", "with_positions_snapshot_count"),
    ("execution_read_only_surfaces_with_fills_snapshot_count", "with_fills_snapshot_count"),
    (
        "execution_read_only_surfaces_with_order_status_snapshot_count",
        "with_order_status_snapshot_count",
    ),
    ("execution_read_only_surfaces_reconciled_venue_count", "reconciled_venue_count"),
    (
        "execution_read_only_surfaces_with_positions_financial_totals_count",
        "with_positions_financial_totals_count",
    ),
    (
        "execution_read_only_surfaces_with_positions_rollover_metrics_count",
        "with_positions_rollover_metrics_count",
    ),
    (
        "execution_read_only_surfaces_with_positions_protection_metrics_count",
        "with_positions_protection_metrics_count",
    ),
    (
        "execution_read_only_surfaces_with_positions_leverage_metrics_count",
        "with_positions_leverage_metrics_count",
    ),
    (
        "execution_read_only_surfaces_with_positions_return_metrics_count",
        "with_positions_return_metrics_count",
    ),
    (
        "execution_read_only_surfaces_with_positions_day_trade_metrics_count",
        "with_positions_day_trade_metrics_count",
    ),
    (
        "execution_read_only_surfaces_with_positions_limit_metrics_count",
        "with_positions_limit_metrics_count",
    ),
    (
        "execution_read_only_surfaces_with_positions_quantity_metrics_count",
        "with_positions_quantity_metrics_count",
    ),
    ("execution_read_only_surfaces_positions_notional_usd_total", "positions_notional_usd_total"),
    (
        "execution_read_only_surfaces_positions_unrealized_pnl_usd_total",
        "positions_unrealized_pnl_usd_total",
    ),
    (
        "execution_read_only_surfaces_positions_collateral_used_usd_total",
        "positions_collateral_used_usd_total",
    ),
    (
        "execution_read_only_surfaces_positions_max_withdrawable_usd_total",
        "positions_max_withdrawable_usd_total",
    ),
    (
        "execution_read_only_surfaces_positions_cumulative_rollover_usd_total",
        "positions_cumulative_rollover_usd_total",
    ),
    (
        "execution_read_only_surfaces_positions_with_liquidation_price_count",
        "positions_with_liquidation_price_count",
    ),
    (
        "execution_read_only_surfaces_positions_with_take_profit_count",
        "positions_with_take_profit_count",
    ),
    (
        "execution_read_only_surfaces_positions_with_stop_loss_count",
        "positions_with_stop_loss_count",
    ),
    ("execution_read_only_surfaces_positions_day_trade_count", "positions_day_trade_count"),
    ("execution_read_only_surfaces_positions_average_leverage", "positions_average_leverage"),
    (
        "execution_read_only_surfaces_positions_average_return_on_equity",
        "positions_average_return_on_equity",
    ),
    ("execution_read_only_surfaces_positions_max_leverage", "positions_max_leverage"),
    ("execution_read_only_surfaces_positions_total_quantity", "positions_total_quantity"),
    ("execution_read_only_surfaces_positions_total_realized_pnl", "positions_total_realized_pnl"),
    (
        "execution_read_only_surfaces_latest_positions_server_time_ms",
        "latest_positions_server_time_ms",
    ),
    (
        "execution_read_only_surfaces_latest_positions_open_timestamp_ms",
        "latest_positions_open_timestamp_ms",
    ),
    ("execution_read_only_surfaces_latest_positions_updated_at", "latest_positions_updated_at"),
    ("execution_read_only_surfaces_latest_positions_client_ts", "latest_positions_client_ts"),
    ("execution_read_only_surfaces_report_path", "execution_read_only_surfaces_report_path"),
)


def read_only_surface_fields(source: Mapping[str, object]) -> dict[str, object]:
    return {
        target: source.get(source_key) for target, source_key in READ_ONLY_SURFACE_FIELD_MAPPING
    }


def _project_fields(
    source: Mapping[str, object], field_mapping: tuple[tuple[str, str], ...]
) -> dict[str, object]:
    return {target: source.get(source_key) for target, source_key in field_mapping}


DAEMON_MANIFEST_FIELD_MAPPING = (
    ("daemon_manifest_mode", "mode"),
    ("daemon_manifest_command", "command"),
    ("daemon_manifest_state_store_path", "state_store_path"),
    ("daemon_manifest_report_path", "daemon_manifest_report_path"),
)

DAEMON_LOOP_FIELD_MAPPING = (
    ("daemon_loop_status", "status"),
    ("daemon_loop_cycles_requested", "cycles_requested"),
    ("daemon_loop_cycles_completed", "cycles_completed"),
    ("daemon_loop_latest_event_status", "latest_event_status"),
    ("daemon_loop_latest_event_exit_code", "latest_event_exit_code"),
    ("daemon_loop_path", "daemon_loop_path"),
    ("daemon_loop_events_path", "daemon_loop_events_path"),
    ("daemon_loop_report_path", "daemon_loop_report_path"),
)

NOTIFICATION_OUTBOX_FIELD_MAPPING = (
    ("notification_outbox_status", "status"),
    ("notification_outbox_sink", "sink"),
    ("notification_outbox_level", "level"),
    ("notification_outbox_title", "title"),
    ("notification_outbox_source", "source"),
    ("notification_outbox_path", "outbox_path"),
    ("notification_outbox_latest_path", "latest_path"),
    ("notification_outbox_report_path", "notification_outbox_report_path"),
)

STATE_EXPORT_FIELD_MAPPING = (
    ("state_export_snapshot_path", "snapshot_path"),
    ("state_export_audit_overall_status", "audit_overall_status"),
    ("state_export_phase_gate_decision", "phase_gate_decision"),
    ("state_export_readiness_next_phase_candidate", "readiness_next_phase_candidate"),
    ("state_export_report_path", "state_export_report_path"),
)

STATE_RESTORE_FIELD_MAPPING = (
    ("state_restore_restored", "restored"),
    ("state_restore_snapshot_path", "snapshot_path"),
    ("state_restore_audit_overall_status", "audit_overall_status"),
    ("state_restore_phase_gate_decision", "phase_gate_decision"),
    ("state_restore_report_path", "state_restore_report_path"),
)


def state_daemon_fields(
    *,
    daemon_manifest: Mapping[str, object],
    daemon_loop: Mapping[str, object],
    notification_outbox: Mapping[str, object],
    state_export: Mapping[str, object],
    state_restore: Mapping[str, object],
) -> dict[str, object]:
    return {
        **_project_fields(daemon_manifest, DAEMON_MANIFEST_FIELD_MAPPING),
        **_project_fields(daemon_loop, DAEMON_LOOP_FIELD_MAPPING),
        **_project_fields(notification_outbox, NOTIFICATION_OUTBOX_FIELD_MAPPING),
        **_project_fields(state_export, STATE_EXPORT_FIELD_MAPPING),
        **_project_fields(state_restore, STATE_RESTORE_FIELD_MAPPING),
    }
