from __future__ import annotations

from sis.reports.operations_dashboard_fields import (
    execution_adapter_fields,
    read_only_surface_fields,
    state_daemon_fields,
)


def test_execution_adapter_fields_prefixes_selected_source_keys_and_omits_extras() -> None:
    fields = execution_adapter_fields(
        {
            "venue": "paper",
            "equity": 1500.0,
            "balance_status_report_path": "data/reports/execution_balance_status.md",
            "unexpected": "ignored",
        },
        prefix="execution_balance_status",
        mapping={
            "venue": "venue",
            "equity": "equity",
            "report_path": "balance_status_report_path",
        },
    )

    assert fields == {
        "execution_balance_status_venue": "paper",
        "execution_balance_status_equity": 1500.0,
        "execution_balance_status_report_path": "data/reports/execution_balance_status.md",
    }


def test_execution_adapter_fields_preserves_missing_keys_as_none() -> None:
    fields = execution_adapter_fields(
        {"venue": "paper"},
        prefix="execution_order_status",
        mapping={"venue": "venue", "status": "status"},
    )

    assert fields == {
        "execution_order_status_venue": "paper",
        "execution_order_status_status": None,
    }


def test_read_only_surface_fields_projects_counts_totals_and_latest_position_keys() -> None:
    fields = read_only_surface_fields(
        {
            "venue_count": 2,
            "with_positions_snapshot_count": 1,
            "positions_notional_usd_total": 5000.0,
            "positions_average_leverage": 3.5,
            "latest_positions_updated_at": "2026-05-24T00:00:00Z",
            "execution_read_only_surfaces_report_path": "data/reports/execution_read_only_surfaces.md",
            "unexpected": "ignored",
        }
    )

    assert fields["execution_read_only_surfaces_venue_count"] == 2
    assert fields["execution_read_only_surfaces_with_positions_snapshot_count"] == 1
    assert fields["execution_read_only_surfaces_positions_notional_usd_total"] == 5000.0
    assert fields["execution_read_only_surfaces_positions_average_leverage"] == 3.5
    assert (
        fields["execution_read_only_surfaces_latest_positions_updated_at"] == "2026-05-24T00:00:00Z"
    )
    assert (
        fields["execution_read_only_surfaces_report_path"]
        == "data/reports/execution_read_only_surfaces.md"
    )
    assert "unexpected" not in fields


def test_read_only_surface_fields_preserves_missing_keys_as_none() -> None:
    fields = read_only_surface_fields({})

    assert fields["execution_read_only_surfaces_venue_count"] is None
    assert fields["execution_read_only_surfaces_positions_total_quantity"] is None
    assert fields["execution_read_only_surfaces_report_path"] is None


def test_state_daemon_fields_projects_daemon_notification_and_state_values() -> None:
    fields = state_daemon_fields(
        daemon_manifest={
            "mode": "paper",
            "command": "uv run sis daemon-loop",
            "daemon_manifest_report_path": "data/reports/daemon_manifest.md",
        },
        daemon_loop={
            "status": "completed",
            "cycles_completed": 1,
            "daemon_loop_report_path": "data/reports/daemon_loop.md",
        },
        notification_outbox={
            "status": "queued",
            "level": "warning",
            "latest_path": "data/notifications/latest.json",
        },
        state_export={
            "phase_gate_decision": "GO",
            "readiness_next_phase_candidate": "Phase 2",
        },
        state_restore={
            "restored": True,
            "state_restore_report_path": "data/reports/state_restore.md",
        },
    )

    assert fields["daemon_manifest_mode"] == "paper"
    assert fields["daemon_manifest_command"] == "uv run sis daemon-loop"
    assert fields["daemon_loop_status"] == "completed"
    assert fields["daemon_loop_cycles_completed"] == 1
    assert fields["notification_outbox_status"] == "queued"
    assert fields["notification_outbox_level"] == "warning"
    assert fields["notification_outbox_latest_path"] == "data/notifications/latest.json"
    assert fields["state_export_phase_gate_decision"] == "GO"
    assert fields["state_export_readiness_next_phase_candidate"] == "Phase 2"
    assert fields["state_restore_restored"] is True
    assert fields["state_restore_report_path"] == "data/reports/state_restore.md"


def test_state_daemon_fields_preserves_missing_values_as_none() -> None:
    fields = state_daemon_fields(
        daemon_manifest={},
        daemon_loop={},
        notification_outbox={},
        state_export={},
        state_restore={},
    )

    assert fields["daemon_manifest_mode"] is None
    assert fields["daemon_loop_report_path"] is None
    assert fields["notification_outbox_report_path"] is None
    assert fields["state_export_report_path"] is None
    assert fields["state_restore_report_path"] is None
