from __future__ import annotations

from sis.reports.paper_cycle_history_latest import latest_note_fields


def test_latest_note_fields_extracts_execution_readiness_and_phase_gate_values() -> None:
    fields = latest_note_fields(
        [
            "execution_overall_status=ok",
            "execution_venue_count=2",
            "execution_comparison_all_registries_present=True",
            "execution_diagnostics_status=degraded",
            "execution_drift_overview_status=degraded",
            "execution_drift_overview_diagnostics_alignment_match=False",
            "execution_drift_overview_state_comparison_mismatching_count=1",
            "execution_drift_overview_snapshot_drift_mismatching_snapshot_count=1",
            "readiness_next_phase=Phase 1",
            "readiness_execution_ready=False",
            "phase_gate_decision=CONDITIONAL_GO_NEEDS_LIVE_WINDOW",
            "phase2_entry_allowed=False",
            "phase_gate_reason=remain_in_phase1_until_live_evidence_gate_clears",
            "phase_gate_strict_validation_passed=False",
            "phase_gate_strict_validation_issue_count=2",
            "phase_gate_checked_files=7",
            "phase_gate_review_report_path=data/reports/phase_gate_review.md",
            "phase_gate_issue_1=data/research/backtest_metrics_summary.json: missing field",
        ]
    )

    assert fields["latest_execution_overall_status"] == "ok"
    assert fields["latest_execution_venue_count"] == "2"
    assert fields["latest_execution_comparison_all_registries_present"] is True
    assert fields["latest_execution_diagnostics_status"] == "degraded"
    assert fields["latest_execution_drift_overview_status"] == "degraded"
    assert fields["latest_readiness_next_phase"] == "Phase 1"
    assert fields["latest_readiness_execution_ready"] == "False"
    assert fields["latest_phase_gate_decision"] == "CONDITIONAL_GO_NEEDS_LIVE_WINDOW"
    assert fields["latest_phase2_entry_allowed"] == "False"
    assert fields["latest_phase_gate_reason"] == "remain_in_phase1_until_live_evidence_gate_clears"
    assert fields["latest_phase_gate_strict_validation_passed"] == "False"
    assert fields["latest_phase_gate_strict_validation_issue_count"] == "2"
    assert fields["latest_phase_gate_checked_files"] == "7"
    assert fields["latest_phase_gate_review_report_path"] == ("data/reports/phase_gate_review.md")
    assert fields["latest_phase_gate_issue_previews"] == [
        "data/research/backtest_metrics_summary.json: missing field"
    ]


def test_latest_note_fields_defaults_missing_values_to_none_and_empty_lists() -> None:
    fields = latest_note_fields([])

    assert fields["latest_execution_diagnostics_status"] is None
    assert fields["latest_execution_drift_overview_status"] is None
    assert fields["latest_readiness_next_phase"] is None
    assert fields["latest_phase_gate_decision"] is None
    assert fields["latest_phase_gate_issue_previews"] == []
