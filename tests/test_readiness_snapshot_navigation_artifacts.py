from __future__ import annotations

from pathlib import Path

from sis.reports.readiness_snapshot_navigation import artifacts_from_paths


def test_artifacts_from_paths_preserves_input_paths_and_restart_pointers() -> None:
    restart_pointers = {
        "readiness_snapshot_report": "data/reports/readiness_snapshot.md",
        "live_evidence_report": "docs/live_evidence_reports/live_evidence_report_run-1.md",
        "extra_restart_pointer": "data/reports/extra.md",
    }

    artifacts = artifacts_from_paths(
        current_state_index_path=Path("data/ops/current_state_index.json"),
        phase_gate_summary_path=Path("data/ops/phase_gate_review_summary.json"),
        execution_snapshot_summary_path=Path("data/ops/execution_snapshot_summary.json"),
        execution_venue_comparison_summary_path=Path(
            "data/ops/execution_venue_comparison_summary.json"
        ),
        execution_venue_diagnostics_summary_path=Path(
            "data/ops/execution_venue_diagnostics_summary.json"
        ),
        execution_gap_history_summary_path=Path("data/ops/execution_gap_history_summary.json"),
        execution_state_comparison_history_summary_path=Path(
            "data/ops/execution_state_comparison_history_summary.json"
        ),
        execution_snapshot_drift_history_summary_path=Path(
            "data/ops/execution_snapshot_drift_history_summary.json"
        ),
        execution_drift_overview_summary_path=Path(
            "data/ops/execution_drift_overview_summary.json"
        ),
        backtest_metrics_summary_path=Path("data/research/backtest_metrics_summary.json"),
        live_evidence_summary_path=Path("data/ops/live_evidence_summary_run-1.json"),
        operations_dashboard_summary_path=Path("data/ops/operations_dashboard_summary.json"),
        restart_pointers=restart_pointers,
    )

    assert artifacts == {
        "current_state_index": "data/ops/current_state_index.json",
        "phase_gate_summary": "data/ops/phase_gate_review_summary.json",
        "execution_snapshot_summary": "data/ops/execution_snapshot_summary.json",
        "execution_venue_comparison_summary": ("data/ops/execution_venue_comparison_summary.json"),
        "execution_venue_diagnostics_summary": (
            "data/ops/execution_venue_diagnostics_summary.json"
        ),
        "execution_gap_history_summary": "data/ops/execution_gap_history_summary.json",
        "execution_state_comparison_history_summary": (
            "data/ops/execution_state_comparison_history_summary.json"
        ),
        "execution_snapshot_drift_history_summary": (
            "data/ops/execution_snapshot_drift_history_summary.json"
        ),
        "execution_drift_overview_summary": "data/ops/execution_drift_overview_summary.json",
        "backtest_metrics_summary": "data/research/backtest_metrics_summary.json",
        "live_evidence_summary": "data/ops/live_evidence_summary_run-1.json",
        "operations_dashboard_summary": "data/ops/operations_dashboard_summary.json",
        "live_evidence_report": "docs/live_evidence_reports/live_evidence_report_run-1.md",
        "readiness_snapshot_report": "data/reports/readiness_snapshot.md",
        "extra_restart_pointer": "data/reports/extra.md",
    }


def test_artifacts_from_paths_preserves_none_shape() -> None:
    artifacts = artifacts_from_paths(
        current_state_index_path=None,
        phase_gate_summary_path=None,
        execution_snapshot_summary_path=None,
        execution_venue_comparison_summary_path=None,
        execution_venue_diagnostics_summary_path=None,
        execution_gap_history_summary_path=None,
        execution_state_comparison_history_summary_path=None,
        execution_snapshot_drift_history_summary_path=None,
        execution_drift_overview_summary_path=None,
        backtest_metrics_summary_path=None,
        live_evidence_summary_path=None,
        operations_dashboard_summary_path=None,
        restart_pointers={"live_evidence_report": None},
    )

    assert artifacts == {
        "current_state_index": None,
        "phase_gate_summary": None,
        "execution_snapshot_summary": None,
        "execution_venue_comparison_summary": None,
        "execution_venue_diagnostics_summary": None,
        "execution_gap_history_summary": None,
        "execution_state_comparison_history_summary": None,
        "execution_snapshot_drift_history_summary": None,
        "execution_drift_overview_summary": None,
        "backtest_metrics_summary": None,
        "live_evidence_summary": None,
        "operations_dashboard_summary": None,
        "live_evidence_report": None,
    }
