from __future__ import annotations

from pathlib import Path

from sis.reports.readiness_snapshot_navigation import restart_pointers_from_paths


def test_restart_pointers_from_paths_preserves_summary_and_report_path_policy() -> None:
    restart_pointers = restart_pointers_from_paths(
        out_path=Path("data/reports/readiness_snapshot.md"),
        current_state_index_path=Path("data/ops/current_state_index.json"),
        operations_dashboard_summary_path=Path("data/ops/operations_dashboard_summary.json"),
        live_evidence_summary_path=Path("data/ops/live_evidence_summary_filename-run.md"),
        live_evidence={"run_id": "payload-run"},
    )

    assert restart_pointers == {
        "readiness_snapshot_report": "data/reports/readiness_snapshot.md",
        "current_state_index_report": "data/reports/current_state_index.md",
        "remediation_planner_summary": "data/ops/remediation_planner_summary.json",
        "remediation_planner_report": "data/reports/remediation_planner.md",
        "remediation_execution_plan_summary": ("data/ops/remediation_execution_plan_summary.json"),
        "remediation_execution_plan_report": "data/reports/remediation_execution_plan.md",
        "remediation_session_summary": "data/ops/remediation_session_summary.json",
        "remediation_session_report": "data/reports/remediation_session.md",
        "remediation_session_checkpoint_summary": (
            "data/ops/remediation_session_checkpoint_summary.json"
        ),
        "remediation_session_checkpoint_report": ("data/reports/remediation_session_checkpoint.md"),
        "remediation_scoreboard_summary": "data/ops/remediation_scoreboard_summary.json",
        "remediation_scoreboard_report": "data/reports/remediation_scoreboard.md",
        "execution_balance_status_report": "data/reports/execution_balance_status.md",
        "execution_fill_status_report": "data/reports/execution_fill_status.md",
        "execution_order_status_report": "data/reports/execution_order_status.md",
        "execution_cancel_order_report": "data/reports/execution_cancel_order.md",
        "execution_close_position_report": "data/reports/execution_close_position.md",
        "execution_reconcile_positions_report": ("data/reports/execution_reconcile_positions.md"),
        "daemon_manifest_report": "data/reports/daemon_manifest.md",
        "daemon_loop_report": "data/reports/daemon_loop.md",
        "notification_outbox_report": "data/reports/notification_outbox.md",
        "state_export_report": "data/reports/state_export.md",
        "state_restore_report": "data/reports/state_restore.md",
        "live_evidence_report": ("docs/live_evidence_reports/live_evidence_report_payload-run.md"),
    }


def test_restart_pointers_from_paths_preserves_none_shape() -> None:
    restart_pointers = restart_pointers_from_paths(
        out_path=None,
        current_state_index_path=None,
        operations_dashboard_summary_path=None,
        live_evidence_summary_path=None,
        live_evidence={},
    )

    assert set(restart_pointers) == {
        "readiness_snapshot_report",
        "current_state_index_report",
        "remediation_planner_summary",
        "remediation_planner_report",
        "remediation_execution_plan_summary",
        "remediation_execution_plan_report",
        "remediation_session_summary",
        "remediation_session_report",
        "remediation_session_checkpoint_summary",
        "remediation_session_checkpoint_report",
        "remediation_scoreboard_summary",
        "remediation_scoreboard_report",
        "execution_balance_status_report",
        "execution_fill_status_report",
        "execution_order_status_report",
        "execution_cancel_order_report",
        "execution_close_position_report",
        "execution_reconcile_positions_report",
        "daemon_manifest_report",
        "daemon_loop_report",
        "notification_outbox_report",
        "state_export_report",
        "state_restore_report",
        "live_evidence_report",
    }
    assert all(value is None for value in restart_pointers.values())
