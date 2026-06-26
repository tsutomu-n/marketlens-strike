from __future__ import annotations

from sis.reports.current_state_index_fields import (
    EXECUTION_ADAPTER_FIELD_KEYS,
    execution_adapter_fields,
)


def test_execution_adapter_fields_preserves_selected_operation_dashboard_keys() -> None:
    source = {
        "execution_balance_status_venue": "paper",
        "execution_fill_status_latest_fill_id": "fill-1",
        "execution_order_status_status": "open",
        "execution_read_only_surfaces_positions_notional_usd_total": 123.45,
        "daemon_loop_status": "ok",
        "notification_outbox_level": "warning",
        "state_restore_restored": True,
        "unexpected_extra_key": "ignored",
    }

    fields = execution_adapter_fields(source)

    assert fields["execution_balance_status_venue"] == "paper"
    assert fields["execution_fill_status_latest_fill_id"] == "fill-1"
    assert fields["execution_order_status_status"] == "open"
    assert fields["execution_read_only_surfaces_positions_notional_usd_total"] == 123.45
    assert fields["daemon_loop_status"] == "ok"
    assert fields["notification_outbox_level"] == "warning"
    assert fields["state_restore_restored"] is True
    assert "unexpected_extra_key" not in fields


def test_execution_adapter_fields_uses_none_for_missing_keys() -> None:
    fields = execution_adapter_fields({})

    assert len(fields) == len(EXECUTION_ADAPTER_FIELD_KEYS)
    assert fields["execution_balance_status_venue"] is None
    assert fields["execution_read_only_surfaces_report_path"] is None
    assert fields["state_export_report_path"] is None
