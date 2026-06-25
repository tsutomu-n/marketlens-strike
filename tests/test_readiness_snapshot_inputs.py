from __future__ import annotations

from sis.reports.readiness_snapshot_inputs import (
    EXECUTION_ADAPTER_FIELD_KEYS,
    execution_adapter_fields,
)


def test_execution_adapter_fields_projects_known_operations_values() -> None:
    source: dict[str, object] = {
        "execution_balance_status_equity": 1500.0,
        "execution_fill_status_latest_fill_id": "fill-1",
        "execution_order_status_status": "working",
        "execution_cancel_order_status": "blocked_read_only",
        "execution_close_position_status": "blocked_read_only",
        "execution_reconcile_positions_matched": 1,
        "execution_read_only_surfaces_venue_count": 2,
        "daemon_manifest_mode": "paper",
        "daemon_loop_status": "completed",
        "notification_outbox_status": "queued",
        "state_export_phase_gate_decision": "GO",
        "state_restore_restored": True,
        "unrelated": "ignored",
    }

    fields = execution_adapter_fields(source)

    assert fields["execution_balance_status_equity"] == 1500.0
    assert fields["execution_fill_status_latest_fill_id"] == "fill-1"
    assert fields["execution_order_status_status"] == "working"
    assert fields["execution_cancel_order_status"] == "blocked_read_only"
    assert fields["execution_close_position_status"] == "blocked_read_only"
    assert fields["execution_reconcile_positions_matched"] == 1
    assert fields["execution_read_only_surfaces_venue_count"] == 2
    assert fields["daemon_manifest_mode"] == "paper"
    assert fields["daemon_loop_status"] == "completed"
    assert fields["notification_outbox_status"] == "queued"
    assert fields["state_export_phase_gate_decision"] == "GO"
    assert fields["state_restore_restored"] is True
    assert "unrelated" not in fields


def test_execution_adapter_fields_preserves_missing_known_keys_as_none() -> None:
    fields = execution_adapter_fields({"execution_balance_status_equity": 1500.0})

    assert set(fields) == set(EXECUTION_ADAPTER_FIELD_KEYS)
    assert fields["execution_balance_status_equity"] == 1500.0
    assert fields["execution_balance_status_currency"] is None
    assert fields["daemon_manifest_command"] is None
    assert fields["notification_outbox_latest_path"] is None
    assert fields["state_restore_report_path"] is None
