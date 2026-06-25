from __future__ import annotations

from sis.commands.runtime_context_notes import (
    _execution_drift_note_lines,
    _execution_summary_note_lines,
    _phase_gate_note_lines,
    _readiness_note_lines,
)


def test_phase_gate_note_lines_preserve_keys_and_issue_notes() -> None:
    assert _phase_gate_note_lines(
        {
            "decision": "hold",
            "phase2_entry_allowed": False,
            "phase_gate_reason": "missing_evidence",
            "phase_gate_strict_validation_passed": False,
            "phase_gate_strict_validation_issue_count": 1,
            "phase_gate_checked_files": 7,
            "phase_gate_strict_validation_issues": [{"message": "missing paper evidence"}],
            "phase_gate_review_report_path": "data/reports/phase_gate_review.md",
        }
    ) == [
        "phase_gate_decision=hold",
        "phase2_entry_allowed=False",
        "phase_gate_reason=missing_evidence",
        "phase_gate_strict_validation_passed=False",
        "phase_gate_strict_validation_issue_count=1",
        "phase_gate_checked_files=7",
        "phase_gate_review_report_path=data/reports/phase_gate_review.md",
        "phase_gate_issue_1=missing paper evidence",
    ]


def test_readiness_note_lines_preserve_next_phase_and_execution_ready_keys() -> None:
    assert _readiness_note_lines(
        {"next_phase_candidate": "paper_observation", "execution_ready": False}
    ) == [
        "readiness_next_phase=paper_observation",
        "readiness_execution_ready=False",
    ]


def test_execution_summary_note_lines_preserve_snapshot_keys() -> None:
    assert _execution_summary_note_lines(
        {
            "overall_status": "blocked",
            "venue_count": 3,
            "execution_snapshot_reason": "read_only_only",
            "execution_snapshot_next_action": "collect_paper_evidence",
        }
    ) == [
        "execution_overall_status=blocked",
        "execution_venue_count=3",
        "execution_snapshot_reason=read_only_only",
        "execution_snapshot_next_action=collect_paper_evidence",
    ]


def test_execution_drift_note_lines_preserve_alignment_keys() -> None:
    assert _execution_drift_note_lines(
        {
            "overall_status": "warn",
            "diagnostics_alignment_match": False,
            "state_comparison_mismatching_count": 2,
            "snapshot_drift_mismatching_snapshot_count": 1,
        }
    ) == [
        "execution_drift_overview_status=warn",
        "execution_drift_overview_diagnostics_alignment_match=False",
        "execution_drift_overview_state_comparison_mismatching_count=2",
        "execution_drift_overview_snapshot_drift_mismatching_snapshot_count=1",
    ]
