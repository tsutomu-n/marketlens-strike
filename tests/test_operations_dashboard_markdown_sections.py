from __future__ import annotations

from sis.reports.operations_dashboard_markdown_sections import (
    decision_state_section_lines,
    overall_section_lines,
)


def _summary() -> dict[str, object]:
    return {
        "overall_status": "blocked",
        "monitoring_status": "degraded",
        "ops_latest_status": "blocked",
        "operations_count": 3,
        "decision_mode": "signal_driven",
        "executed_count": 2,
        "blocked_count": 1,
        "execution_overall_status": "ok",
        "execution_venue_count": 2,
        "execution_comparison_all_registries_present": True,
        "execution_diagnostics_status": "degraded",
        "execution_balance_gap_detected": True,
        "execution_fills_gap_detected": False,
        "execution_gap_history_entry_count": 4,
        "execution_gap_history_latest_status": "ok",
        "execution_gap_history_latest_diagnostics_status": "degraded",
        "execution_state_comparison_entry_count": 4,
        "execution_state_comparison_latest_status_match": False,
        "execution_state_comparison_mismatching_count": 1,
        "execution_snapshot_drift_entry_count": 3,
        "execution_snapshot_drift_latest_status_match": True,
        "execution_snapshot_drift_mismatching_snapshot_count": 1,
        "execution_drift_overview_status": "degraded",
        "execution_drift_overview_diagnostics_alignment_match": False,
        "execution_drift_overview_state_comparison_mismatching_count": 1,
        "execution_drift_overview_snapshot_drift_mismatching_snapshot_count": 1,
    }


def test_overall_section_lines_preserve_exact_order() -> None:
    assert overall_section_lines(_summary()) == [
        "## Overall",
        "",
        "- overall_status: blocked",
        "- monitoring_status: degraded",
        "- ops_latest_status: blocked",
        "- operations_count: 3",
    ]


def test_decision_state_section_lines_preserve_exact_order() -> None:
    assert decision_state_section_lines(_summary()) == [
        "## Decision State",
        "",
        "- decision_mode: signal_driven",
        "- executed_count: 2",
        "- blocked_count: 1",
        "- execution_overall_status: ok",
        "- execution_venue_count: 2",
        "- execution_comparison_all_registries_present: True",
        "- execution_diagnostics_status: degraded",
        "- execution_balance_gap_detected: True",
        "- execution_fills_gap_detected: False",
        "- execution_gap_history_entry_count: 4",
        "- execution_gap_history_latest_status: ok",
        "- execution_gap_history_latest_diagnostics_status: degraded",
        "- execution_state_comparison_entry_count: 4",
        "- execution_state_comparison_latest_status_match: False",
        "- execution_state_comparison_mismatching_count: 1",
        "- execution_snapshot_drift_entry_count: 3",
        "- execution_snapshot_drift_latest_status_match: True",
        "- execution_snapshot_drift_mismatching_snapshot_count: 1",
        "- execution_drift_overview_status: degraded",
        "- execution_drift_overview_diagnostics_alignment_match: False",
        "- execution_drift_overview_state_comparison_mismatching_count: 1",
        "- execution_drift_overview_snapshot_drift_mismatching_snapshot_count: 1",
    ]
