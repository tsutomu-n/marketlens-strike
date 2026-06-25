from __future__ import annotations

from sis.reports.readiness_snapshot_order import (
    READINESS_SNAPSHOT_RECOMMENDED_EXTRA_PATHS,
    readiness_snapshot_recommended_read_order,
)


def test_readiness_snapshot_recommended_read_order_preserves_final_order() -> None:
    assert readiness_snapshot_recommended_read_order() == [
        "docs/CURRENT_STATE.md",
        "docs/CODE_STATUS.md",
        "data/ops/readiness_snapshot.json",
        "data/reports/readiness_snapshot.md",
        "data/ops/current_state_index.json",
        "data/reports/current_state_index.md",
        "data/reports/remediation_scoreboard.md",
        "data/reports/remediation_session_checkpoint.md",
        "data/reports/remediation_session.md",
        "data/reports/remediation_execution_plan.md",
        "data/reports/remediation_planner.md",
        "data/ops/phase_gate_review_summary.json",
        "data/ops/execution_snapshot_summary.json",
        "data/ops/execution_venue_comparison_summary.json",
        "data/ops/execution_venue_diagnostics_summary.json",
        "data/ops/execution_gap_history_summary.json",
        "data/ops/execution_state_comparison_history_summary.json",
        "data/ops/execution_snapshot_drift_history_summary.json",
        "data/ops/execution_drift_overview_summary.json",
        "data/reports/execution_balance_status.md",
        "data/reports/execution_fill_status.md",
        "data/reports/execution_order_status.md",
        "data/reports/execution_cancel_order.md",
        "data/reports/execution_close_position.md",
        "data/reports/execution_reconcile_positions.md",
        "data/reports/daemon_manifest.md",
        "data/reports/daemon_loop.md",
        "data/reports/notification_outbox.md",
        "data/reports/state_export.md",
        "data/reports/state_restore.md",
        "docs/live_evidence_reports/live_evidence_report_<run_id>.md",
        "data/research/backtest_metrics_summary.json",
        "data/reports/phase_gate_review.md",
        "data/reports/operations_dashboard.md",
        "docs/OPERATIONS_RUNBOOK.md",
        "docs/ARCHITECTURE_AND_PHASES.md",
    ]


def test_readiness_snapshot_recommended_extra_paths_are_immutable() -> None:
    assert isinstance(READINESS_SNAPSHOT_RECOMMENDED_EXTRA_PATHS, tuple)
    assert READINESS_SNAPSHOT_RECOMMENDED_EXTRA_PATHS[0] == "data/ops/readiness_snapshot.json"
    assert (
        READINESS_SNAPSHOT_RECOMMENDED_EXTRA_PATHS[-1]
        == "data/research/backtest_metrics_summary.json"
    )
