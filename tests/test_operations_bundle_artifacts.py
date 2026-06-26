from __future__ import annotations

from pathlib import Path

from sis.reports.operations_bundle_artifacts import (
    artifact_paths,
    recommended_read_order_items,
)


def test_artifact_paths_preserves_existing_keys_and_string_values() -> None:
    paths = artifact_paths(
        monitoring_summary_path=Path("data/ops/monitoring.json"),
        ops_review_summary_path=Path("data/ops/ops_review_summary.json"),
        dashboard_summary_path=Path("data/ops/operations_dashboard_summary.json"),
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
        readiness_summary_path=Path("data/ops/readiness_snapshot.json"),
        runbook_summary_path=Path("data/ops/paper_operations_runbook_summary.json"),
        paper_cycle_history_summary_path=Path("data/ops/paper_cycle_history_summary.json"),
        phase_gate_summary_path=Path("data/ops/phase_gate_review_summary.json"),
    )

    assert list(paths) == [
        "monitoring_summary",
        "ops_review_summary",
        "dashboard_summary",
        "execution_snapshot_summary",
        "execution_venue_comparison_summary",
        "execution_venue_diagnostics_summary",
        "execution_gap_history_summary",
        "execution_state_comparison_history_summary",
        "execution_snapshot_drift_history_summary",
        "execution_drift_overview_summary",
        "readiness_summary",
        "runbook_summary",
        "paper_cycle_history_summary",
        "phase_gate_summary",
    ]
    assert paths["monitoring_summary"] == "data/ops/monitoring.json"
    assert (
        paths["execution_state_comparison_history_summary"]
        == "data/ops/execution_state_comparison_history_summary.json"
    )
    assert paths["phase_gate_summary"] == "data/ops/phase_gate_review_summary.json"


def test_artifact_paths_preserves_missing_paths_as_none() -> None:
    paths = artifact_paths(
        monitoring_summary_path=None,
        ops_review_summary_path=None,
        dashboard_summary_path=None,
        execution_snapshot_summary_path=None,
        execution_venue_comparison_summary_path=None,
        execution_venue_diagnostics_summary_path=None,
        execution_gap_history_summary_path=None,
        execution_state_comparison_history_summary_path=None,
        execution_snapshot_drift_history_summary_path=None,
        execution_drift_overview_summary_path=None,
        readiness_summary_path=None,
        runbook_summary_path=None,
        paper_cycle_history_summary_path=None,
        phase_gate_summary_path=None,
    )

    assert set(paths.values()) == {None}
    assert paths["execution_drift_overview_summary"] is None


def test_recommended_read_order_items_preserves_operations_bundle_order() -> None:
    assert recommended_read_order_items() == [
        "docs/CURRENT_STATE.md",
        "docs/CODE_STATUS.md",
        "data/ops/execution_snapshot_summary.json",
        "data/ops/execution_venue_comparison_summary.json",
        "data/ops/execution_venue_diagnostics_summary.json",
        "data/ops/execution_gap_history_summary.json",
        "data/ops/execution_state_comparison_history_summary.json",
        "data/ops/execution_snapshot_drift_history_summary.json",
        "data/ops/execution_drift_overview_summary.json",
        "data/ops/readiness_snapshot.json",
        "data/ops/operations_dashboard_summary.json",
        "data/ops/audit_dashboard_summary.json",
        "data/ops/operations_bundle_manifest.json",
        "data/ops/audit_bundle_manifest.json",
        "data/reports/operations_dashboard.md",
        "data/reports/audit_dashboard.md",
        "data/reports/operations_audit_pack.md",
        "data/reports/paper_operations_runbook.md",
        "data/reports/current_state_index.md",
        "data/reports/readiness_snapshot.md",
        "data/reports/phase_gate_review.md",
        "data/reports/remediation_scoreboard.md",
        "docs/OPERATIONS_RUNBOOK.md",
        "docs/ARCHITECTURE_AND_PHASES.md",
    ]
