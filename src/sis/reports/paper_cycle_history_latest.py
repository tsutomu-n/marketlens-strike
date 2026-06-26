from __future__ import annotations

from typing import Any

from sis.reports import paper_cycle_history_notes
from sis.reports.summary_normalizers import (
    latest_execution_lineage_from_notes,
    phase_gate_issue_note_previews,
)

_note_value = paper_cycle_history_notes.note_value


def latest_note_fields(notes: list[object]) -> dict[str, Any]:
    return {
        **latest_execution_lineage_from_notes(notes),
        "latest_execution_diagnostics_status": _note_value(notes, "execution_diagnostics_status="),
        "latest_execution_drift_overview_status": _note_value(
            notes, "execution_drift_overview_status="
        ),
        "latest_execution_drift_overview_diagnostics_alignment_match": _note_value(
            notes,
            "execution_drift_overview_diagnostics_alignment_match=",
        ),
        "latest_execution_drift_overview_state_comparison_mismatching_count": _note_value(
            notes,
            "execution_drift_overview_state_comparison_mismatching_count=",
        ),
        "latest_execution_drift_overview_snapshot_drift_mismatching_snapshot_count": (
            _note_value(
                notes,
                "execution_drift_overview_snapshot_drift_mismatching_snapshot_count=",
            )
        ),
        "latest_readiness_next_phase": _note_value(notes, "readiness_next_phase="),
        "latest_readiness_execution_ready": _note_value(notes, "readiness_execution_ready="),
        "latest_phase_gate_decision": _note_value(notes, "phase_gate_decision="),
        "latest_phase2_entry_allowed": _note_value(notes, "phase2_entry_allowed="),
        "latest_phase_gate_reason": _note_value(notes, "phase_gate_reason="),
        "latest_phase_gate_strict_validation_passed": _note_value(
            notes,
            "phase_gate_strict_validation_passed=",
        ),
        "latest_phase_gate_strict_validation_issue_count": _note_value(
            notes,
            "phase_gate_strict_validation_issue_count=",
        ),
        "latest_phase_gate_checked_files": _note_value(notes, "phase_gate_checked_files="),
        "latest_phase_gate_review_report_path": _note_value(
            notes,
            "phase_gate_review_report_path=",
        ),
        "latest_phase_gate_issue_previews": phase_gate_issue_note_previews(notes),
    }
