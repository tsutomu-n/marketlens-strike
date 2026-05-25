from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sis.reports.summary_normalizers import (
    execution_comparison_flat_fields,
    execution_diagnostics_flat_fields,
    execution_gap_history_flat_fields,
    execution_drift_overview_flat_fields,
    execution_snapshot_drift_flat_fields,
    execution_snapshot_flat_fields,
    execution_state_comparison_flat_fields,
    normalize_execution_comparison_summary,
    normalize_execution_diagnostics_summary,
    normalize_execution_drift_overview_summary,
    normalize_execution_gap_history_summary,
    normalize_execution_snapshot_drift_summary,
    normalize_execution_snapshot_summary,
    normalize_execution_state_comparison_summary,
    normalize_phase_gate_summary,
    normalize_readiness_summary,
    latest_execution_lineage_fields_from_summary,
    phase_gate_flat_fields,
    readiness_flat_fields,
)
from sis.storage.jsonl_store import write_json


@dataclass(frozen=True)
class ScheduledRun:
    run_type: str
    scheduled_for: datetime
    command: str
    notes: list[str]


def schedule_run(
    *,
    run_type: str,
    scheduled_for: datetime,
    command: str,
    notes: list[str] | None = None,
) -> ScheduledRun:
    normalized = scheduled_for.astimezone(timezone.utc) if scheduled_for.tzinfo else scheduled_for.replace(tzinfo=timezone.utc)
    return ScheduledRun(
        run_type=run_type,
        scheduled_for=normalized,
        command=command,
        notes=notes or [],
    )


def next_interval_run(*, run_type: str, every_minutes: int, command: str, now: datetime | None = None) -> ScheduledRun:
    current = now.astimezone(timezone.utc) if now and now.tzinfo else (now or datetime.now(timezone.utc))
    delta = timedelta(minutes=every_minutes)
    return schedule_run(
        run_type=run_type,
        scheduled_for=current + delta,
        command=command,
        notes=[f"interval_minutes={every_minutes}"],
    )


def write_schedule(path: Path, run: ScheduledRun) -> Path:
    write_json(
        path,
        {
            "run_type": run.run_type,
            "scheduled_for": run.scheduled_for.isoformat(),
            "command": run.command,
            "notes": run.notes,
        },
    )
    return path


def write_schedule_with_audit(
    path: Path,
    run: ScheduledRun,
    *,
    audit_summary: dict | None = None,
    phase_gate_summary: dict | None = None,
    execution_summary: dict | None = None,
    execution_comparison_summary: dict | None = None,
    execution_diagnostics_summary: dict | None = None,
    execution_gap_history_summary: dict | None = None,
    execution_state_comparison_summary: dict | None = None,
    execution_snapshot_drift_summary: dict | None = None,
    execution_drift_overview_summary: dict | None = None,
    readiness_summary: dict | None = None,
) -> Path:
    normalized_phase_gate_summary = normalize_phase_gate_summary(phase_gate_summary)
    normalized_execution_summary = normalize_execution_snapshot_summary(execution_summary)
    normalized_execution_comparison_summary = normalize_execution_comparison_summary(
        execution_comparison_summary
    )
    normalized_execution_diagnostics_summary = normalize_execution_diagnostics_summary(
        execution_diagnostics_summary
    )
    normalized_execution_gap_history_summary = normalize_execution_gap_history_summary(
        execution_gap_history_summary
    )
    normalized_execution_state_comparison_summary = normalize_execution_state_comparison_summary(
        execution_state_comparison_summary
    )
    normalized_execution_snapshot_drift_summary = normalize_execution_snapshot_drift_summary(
        execution_snapshot_drift_summary
    )
    normalized_execution_drift_overview_summary = normalize_execution_drift_overview_summary(
        execution_drift_overview_summary
    )
    normalized_readiness_summary = normalize_readiness_summary(readiness_summary)
    phase_gate_fields = phase_gate_flat_fields(normalized_phase_gate_summary)
    execution_fields = execution_snapshot_flat_fields(normalized_execution_summary)
    execution_comparison_fields = execution_comparison_flat_fields(
        normalized_execution_comparison_summary
    )
    execution_diagnostics_fields = execution_diagnostics_flat_fields(
        normalized_execution_diagnostics_summary
    )
    execution_gap_history_fields = execution_gap_history_flat_fields(
        normalized_execution_gap_history_summary
    )
    execution_state_comparison_fields = execution_state_comparison_flat_fields(
        normalized_execution_state_comparison_summary
    )
    execution_snapshot_drift_fields = execution_snapshot_drift_flat_fields(
        normalized_execution_snapshot_drift_summary
    )
    readiness_fields = readiness_flat_fields(normalized_readiness_summary)
    execution_drift_fields = execution_drift_overview_flat_fields(
        normalized_execution_drift_overview_summary
    )
    lineage_payload = audit_summary if isinstance(audit_summary, dict) else {}
    latest_execution_lineage = latest_execution_lineage_fields_from_summary(lineage_payload)
    write_json(
        path,
        {
            "run_type": run.run_type,
            "scheduled_for": run.scheduled_for.isoformat(),
            "command": run.command,
            "notes": run.notes,
            "audit": audit_summary or {},
            "audit_summary": audit_summary or {},
            **latest_execution_lineage,
            "phase_gate": normalized_phase_gate_summary,
            "phase_gate_summary": normalized_phase_gate_summary,
            **phase_gate_fields,
            "phase2_entry_reason": phase_gate_fields.get("phase2_entry_reason"),
            "execution": normalized_execution_summary,
            "execution_summary": normalized_execution_summary,
            **execution_fields,
            "execution_comparison": normalized_execution_comparison_summary,
            "execution_comparison_summary": normalized_execution_comparison_summary,
            **execution_comparison_fields,
            "execution_diagnostics": normalized_execution_diagnostics_summary,
            "execution_diagnostics_summary": normalized_execution_diagnostics_summary,
            **execution_diagnostics_fields,
            "execution_gap_history": normalized_execution_gap_history_summary,
            "execution_gap_history_summary": normalized_execution_gap_history_summary,
            **execution_gap_history_fields,
            "execution_state_comparison": normalized_execution_state_comparison_summary,
            "execution_state_comparison_summary": normalized_execution_state_comparison_summary,
            **execution_state_comparison_fields,
            "execution_snapshot_drift": normalized_execution_snapshot_drift_summary,
            "execution_snapshot_drift_summary": normalized_execution_snapshot_drift_summary,
            **execution_snapshot_drift_fields,
            "execution_drift_overview": normalized_execution_drift_overview_summary,
            "execution_drift_overview_summary": normalized_execution_drift_overview_summary,
            **execution_drift_fields,
            "readiness": normalized_readiness_summary,
            "readiness_summary": normalized_readiness_summary,
            **readiness_fields,
        },
    )
    return path
