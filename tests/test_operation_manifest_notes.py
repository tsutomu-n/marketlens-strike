from __future__ import annotations

from pathlib import Path

from sis.commands.operation_manifest_notes import (
    operations_manifest_context_note_lines,
    remediation_manifest_context_note_lines,
)


def test_operations_manifest_context_note_lines_preserve_suffix_order(
    tmp_path: Path, monkeypatch
) -> None:
    import sis.commands.operation_manifest_notes as notes

    monkeypatch.setattr(notes, "read_execution_schedule_summary", lambda _: {"id": "execution"})
    monkeypatch.setattr(
        notes,
        "read_execution_comparison_schedule_summary",
        lambda _: {"id": "comparison"},
    )
    monkeypatch.setattr(
        notes,
        "read_execution_diagnostics_schedule_summary",
        lambda _: {"id": "diagnostics"},
    )
    monkeypatch.setattr(
        notes,
        "read_execution_gap_history_schedule_summary",
        lambda _: {"id": "gap_history"},
    )
    monkeypatch.setattr(
        notes,
        "read_execution_state_comparison_schedule_summary",
        lambda _: {"id": "state_comparison"},
    )
    monkeypatch.setattr(
        notes,
        "read_execution_snapshot_drift_schedule_summary",
        lambda _: {"id": "snapshot_drift"},
    )
    monkeypatch.setattr(
        notes,
        "read_execution_drift_overview_schedule_summary",
        lambda _: {"id": "drift_overview"},
    )
    monkeypatch.setattr(notes, "read_readiness_schedule_summary", lambda _: {"id": "readiness"})
    monkeypatch.setattr(notes, "read_phase_gate_schedule_summary", lambda _: {"id": "phase_gate"})
    monkeypatch.setattr(
        notes,
        "_execution_summary_note_lines",
        lambda payload: [f"{payload['id']}_line"],
    )
    monkeypatch.setattr(
        notes,
        "_execution_comparison_note_lines",
        lambda payload: [f"{payload['id']}_line"],
    )
    monkeypatch.setattr(
        notes,
        "_execution_diagnostics_note_lines",
        lambda payload: [f"{payload['id']}_line"],
    )
    monkeypatch.setattr(
        notes,
        "_execution_gap_history_note_lines",
        lambda payload: [f"{payload['id']}_line"],
    )
    monkeypatch.setattr(
        notes,
        "_execution_state_comparison_note_lines",
        lambda payload: [f"{payload['id']}_line"],
    )
    monkeypatch.setattr(
        notes,
        "_execution_snapshot_drift_note_lines",
        lambda payload: [f"{payload['id']}_line"],
    )
    monkeypatch.setattr(
        notes,
        "_execution_drift_note_lines",
        lambda payload: [f"{payload['id']}_line"],
    )
    monkeypatch.setattr(notes, "_readiness_note_lines", lambda payload: [f"{payload['id']}_line"])
    monkeypatch.setattr(notes, "_phase_gate_note_lines", lambda payload: [f"{payload['id']}_line"])

    assert operations_manifest_context_note_lines(tmp_path) == [
        "execution_line",
        "comparison_line",
        "diagnostics_line",
        "gap_history_line",
        "state_comparison_line",
        "snapshot_drift_line",
        "drift_overview_line",
        "readiness_line",
        "phase_gate_line",
    ]


def test_remediation_manifest_context_note_lines_preserve_suffix_order(
    tmp_path: Path, monkeypatch
) -> None:
    import sis.commands.operation_manifest_notes as notes

    monkeypatch.setattr(notes, "read_readiness_schedule_summary", lambda _: {"id": "readiness"})
    monkeypatch.setattr(notes, "read_phase_gate_schedule_summary", lambda _: {"id": "phase_gate"})
    monkeypatch.setattr(notes, "_readiness_note_lines", lambda payload: [f"{payload['id']}_line"])
    monkeypatch.setattr(notes, "_phase_gate_note_lines", lambda payload: [f"{payload['id']}_line"])

    assert remediation_manifest_context_note_lines(tmp_path) == [
        "readiness_line",
        "phase_gate_line",
    ]
