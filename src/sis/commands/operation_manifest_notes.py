from __future__ import annotations

from pathlib import Path

from sis.commands.runtime_context_notes import (
    _execution_comparison_note_lines,
    _execution_diagnostics_note_lines,
    _execution_drift_note_lines,
    _execution_gap_history_note_lines,
    _execution_snapshot_drift_note_lines,
    _execution_state_comparison_note_lines,
    _execution_summary_note_lines,
    _phase_gate_note_lines,
    _readiness_note_lines,
)
from sis.commands.runtime_schedule_summaries import (
    read_execution_comparison_schedule_summary,
    read_execution_diagnostics_schedule_summary,
    read_execution_drift_overview_schedule_summary,
    read_execution_gap_history_schedule_summary,
    read_execution_schedule_summary,
    read_execution_snapshot_drift_schedule_summary,
    read_execution_state_comparison_schedule_summary,
    read_phase_gate_schedule_summary,
    read_readiness_schedule_summary,
)


def operations_manifest_context_note_lines(settings_data_dir: Path) -> list[str]:
    execution = read_execution_schedule_summary(settings_data_dir)
    execution_comparison = read_execution_comparison_schedule_summary(settings_data_dir)
    execution_diagnostics = read_execution_diagnostics_schedule_summary(settings_data_dir)
    gap_history = read_execution_gap_history_schedule_summary(settings_data_dir)
    state_comparison = read_execution_state_comparison_schedule_summary(settings_data_dir)
    snapshot_drift = read_execution_snapshot_drift_schedule_summary(settings_data_dir)
    drift_overview = read_execution_drift_overview_schedule_summary(settings_data_dir)
    readiness = read_readiness_schedule_summary(settings_data_dir)
    phase_gate = read_phase_gate_schedule_summary(settings_data_dir)
    return [
        *_execution_summary_note_lines(execution),
        *_execution_comparison_note_lines(execution_comparison),
        *_execution_diagnostics_note_lines(execution_diagnostics),
        *_execution_gap_history_note_lines(gap_history),
        *_execution_state_comparison_note_lines(state_comparison),
        *_execution_snapshot_drift_note_lines(snapshot_drift),
        *_execution_drift_note_lines(drift_overview),
        *_readiness_note_lines(readiness),
        *_phase_gate_note_lines(phase_gate),
    ]


def remediation_manifest_context_note_lines(settings_data_dir: Path) -> list[str]:
    readiness = read_readiness_schedule_summary(settings_data_dir)
    phase_gate = read_phase_gate_schedule_summary(settings_data_dir)
    return [
        *_readiness_note_lines(readiness),
        *_phase_gate_note_lines(phase_gate),
    ]
