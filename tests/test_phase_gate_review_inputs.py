from __future__ import annotations

import json
from pathlib import Path

from sis.reports.phase_gate_review_inputs import load_phase_gate_execution_inputs


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_load_phase_gate_execution_inputs_returns_payloads_and_flat_fields(
    tmp_path: Path,
) -> None:
    snapshot_path = tmp_path / "ops/execution_snapshot_summary.json"
    comparison_path = tmp_path / "ops/execution_venue_comparison_summary.json"
    diagnostics_path = tmp_path / "ops/execution_venue_diagnostics_summary.json"
    gap_history_path = tmp_path / "ops/execution_gap_history_summary.json"
    state_comparison_path = tmp_path / "ops/execution_state_comparison_history_summary.json"
    snapshot_drift_path = tmp_path / "ops/execution_snapshot_drift_history_summary.json"
    drift_overview_path = tmp_path / "ops/execution_drift_overview_summary.json"

    _write_json(snapshot_path, {"overall_status": "ok", "venue_count": 2})
    _write_json(comparison_path, {"all_registries_present": True})
    _write_json(
        diagnostics_path,
        {
            "overall_status": "degraded",
            "balance_gap_detected": True,
            "fills_gap_detected": False,
        },
    )
    _write_json(
        gap_history_path,
        {
            "entry_count": 4,
            "latest_status": "ok",
            "latest_execution_diagnostics_status": "degraded",
        },
    )
    _write_json(
        state_comparison_path,
        {"entry_count": 2, "latest_status_match": True, "mismatching_count": 0},
    )
    _write_json(
        snapshot_drift_path,
        {
            "entry_count": 3,
            "latest_execution_state_comparison_status_match": True,
            "mismatching_snapshot_count": 1,
        },
    )
    _write_json(
        drift_overview_path,
        {
            "execution_drift_overview_status": "degraded",
            "execution_drift_overview_diagnostics_alignment_match": False,
            "execution_drift_overview_state_comparison_mismatching_count": 1,
            "execution_drift_overview_snapshot_drift_mismatching_snapshot_count": 2,
        },
    )

    inputs = load_phase_gate_execution_inputs(
        execution_snapshot_summary_path=snapshot_path,
        execution_venue_comparison_summary_path=comparison_path,
        execution_venue_diagnostics_summary_path=diagnostics_path,
        execution_gap_history_summary_path=gap_history_path,
        execution_state_comparison_history_summary_path=state_comparison_path,
        execution_snapshot_drift_history_summary_path=snapshot_drift_path,
        execution_drift_overview_summary_path=drift_overview_path,
    )

    assert inputs.execution_summary == {"overall_status": "ok", "venue_count": 2}
    assert inputs.execution_comparison == {"all_registries_present": True}
    assert inputs.execution_diagnostics["overall_status"] == "degraded"
    assert inputs.execution_gap_history["entry_count"] == 4
    assert inputs.execution_state_comparison["latest_status_match"] is True
    assert inputs.execution_snapshot_drift["mismatching_snapshot_count"] == 1
    assert inputs.execution_drift_overview["execution_drift_overview_status"] == "degraded"
    assert inputs.flat_fields["execution_overall_status"] == "ok"
    assert inputs.flat_fields["execution_venue_count"] == 2
    assert inputs.flat_fields["execution_comparison_all_registries_present"] is True
    assert inputs.flat_fields["execution_diagnostics_status"] == "degraded"
    assert inputs.flat_fields["execution_balance_gap_detected"] is True
    assert inputs.flat_fields["execution_gap_history_entry_count"] == 4
    assert inputs.flat_fields["execution_state_comparison_latest_status_match"] is True
    assert inputs.flat_fields["execution_snapshot_drift_mismatching_snapshot_count"] == 1
    assert inputs.flat_fields["execution_drift_overview_status"] == "degraded"
    assert (
        inputs.flat_fields["execution_drift_overview_snapshot_drift_mismatching_snapshot_count"]
        == 2
    )
