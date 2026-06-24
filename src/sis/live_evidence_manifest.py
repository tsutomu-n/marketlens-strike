from __future__ import annotations

import json
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field

from sis.reports.loaders import safe_read_json_dict
from sis.reports.summary_normalizers import (
    execution_drift_overview_flat_fields,
    latest_execution_lineage_fields_from_payload,
    normalize_execution_comparison_summary,
    normalize_execution_diagnostics_summary,
    normalize_execution_drift_overview_summary,
    normalize_execution_gap_history_summary,
    normalize_execution_snapshot_drift_summary,
    normalize_execution_snapshot_summary,
    normalize_execution_state_comparison_summary,
    normalize_phase_gate_summary,
    normalize_readiness_summary,
    phase_gate_flat_fields,
    readiness_flat_fields,
)


class StepOutcome(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    COMPLETED_WITH_RETRIES = "completed_with_retries"
    FAILED = "failed"
    SKIPPED = "skipped"


class RunOutcome(str, Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    COMPLETED_WITH_RETRIES = "completed_with_retries"
    PARTIAL_FAILED = "partial_failed"
    FAILED_PREFLIGHT = "failed_preflight"
    FAILED_COLLECTION = "failed_collection"


TERMINAL_RUN_OUTCOMES = {
    RunOutcome.COMPLETED,
    RunOutcome.COMPLETED_WITH_RETRIES,
    RunOutcome.PARTIAL_FAILED,
    RunOutcome.FAILED_PREFLIGHT,
    RunOutcome.FAILED_COLLECTION,
}


class StepRecord(BaseModel):
    name: str
    status: StepOutcome = StepOutcome.PENDING
    attempt_count: int = 0
    started_at_utc: str | None = None
    ended_at_utc: str | None = None
    error_summary: str | None = None
    command: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class LiveEvidenceManifest(BaseModel):
    run_id: str
    status: RunOutcome = RunOutcome.RUNNING
    requested_schedule_jst: str | None = None
    log_path: str | None = None
    manifest_path: str | None = None
    started_at_utc: str | None = None
    finished_at_utc: str | None = None
    duration_minutes: int
    metadata_interval_seconds: int
    force: bool = False
    data_dir: str = "data"
    step_order: list[str] = Field(default_factory=list)
    steps: list[StepRecord] = Field(default_factory=list)
    row_counts: dict[str, int] = Field(default_factory=dict)
    artifacts: dict[str, str | None] = Field(default_factory=dict)
    diagnostics: list[dict] = Field(default_factory=list)
    decision: str | None = None
    blockers: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    phase_gate_summary: dict[str, object] = Field(default_factory=dict)
    phase_gate_decision: str | None = None
    phase2_entry_allowed: bool | None = None
    phase_gate_reason: str | None = None
    phase_gate_strict_validation_passed: bool | None = None
    phase_gate_strict_validation_issue_count: int | None = None
    phase_gate_checked_files: int | None = None
    strict_validation_passed: bool | None = None
    readiness_summary: dict[str, object] = Field(default_factory=dict)
    readiness_next_phase_candidate: str | None = None
    readiness_execution_ready: bool | None = None
    timeline_latest_execution_summary: dict[str, object] = Field(default_factory=dict)
    timeline_latest_execution_comparison_summary: dict[str, object] = Field(default_factory=dict)
    timeline_latest_execution_overall_status: str | None = None
    timeline_latest_execution_venue_count: int | None = None
    timeline_latest_execution_comparison_all_registries_present: bool | None = None
    bundle_history_latest_execution_summary: dict[str, object] = Field(default_factory=dict)
    bundle_history_latest_execution_comparison_summary: dict[str, object] = Field(
        default_factory=dict
    )
    bundle_history_latest_execution_overall_status: str | None = None
    bundle_history_latest_execution_venue_count: int | None = None
    bundle_history_latest_execution_comparison_all_registries_present: bool | None = None
    cycle_history_latest_execution_summary: dict[str, object] = Field(default_factory=dict)
    cycle_history_latest_execution_comparison_summary: dict[str, object] = Field(
        default_factory=dict
    )
    cycle_history_latest_execution_overall_status: str | None = None
    cycle_history_latest_execution_venue_count: int | None = None
    cycle_history_latest_execution_comparison_all_registries_present: bool | None = None
    execution_summary: dict[str, object] = Field(default_factory=dict)
    execution_comparison_summary: dict[str, object] = Field(default_factory=dict)
    execution_diagnostics_summary: dict[str, object] = Field(default_factory=dict)
    execution_gap_history_summary: dict[str, object] = Field(default_factory=dict)
    execution_state_comparison_summary: dict[str, object] = Field(default_factory=dict)
    execution_snapshot_drift_summary: dict[str, object] = Field(default_factory=dict)
    execution_drift_overview_summary: dict[str, object] = Field(default_factory=dict)
    execution_drift_overview_status: str | None = None
    execution_drift_overview_diagnostics_alignment_match: bool | None = None
    execution_drift_overview_state_comparison_mismatching_count: int | None = None
    execution_drift_overview_snapshot_drift_mismatching_snapshot_count: int | None = None
    failure_summary: str | None = None


def apply_latest_execution_lineage(
    manifest: LiveEvidenceManifest,
    latest_execution_lineage: dict[str, object],
) -> None:
    for prefix in (
        "timeline_latest",
        "bundle_history_latest",
        "cycle_history_latest",
    ):
        setattr(
            manifest,
            f"{prefix}_execution_summary",
            latest_execution_lineage.get(f"{prefix}_execution_summary", {}),
        )
        setattr(
            manifest,
            f"{prefix}_execution_comparison_summary",
            latest_execution_lineage.get(f"{prefix}_execution_comparison_summary", {}),
        )
        setattr(
            manifest,
            f"{prefix}_execution_overall_status",
            latest_execution_lineage.get(f"{prefix}_execution_overall_status"),
        )
        setattr(
            manifest,
            f"{prefix}_execution_venue_count",
            latest_execution_lineage.get(f"{prefix}_execution_venue_count"),
        )
        setattr(
            manifest,
            f"{prefix}_execution_comparison_all_registries_present",
            latest_execution_lineage.get(f"{prefix}_execution_comparison_all_registries_present"),
        )


def default_manifest_path(run_id: str) -> Path:
    return Path("logs/live_evidence/manifests") / f"live_evidence_{run_id}.json"


def load_manifest(path: Path) -> LiveEvidenceManifest:
    payload = safe_read_json_dict(path)
    return LiveEvidenceManifest.model_validate(payload)


def write_manifest(path: Path, manifest: LiveEvidenceManifest) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    if isinstance(manifest.phase_gate_summary, dict):
        manifest.phase_gate_summary = normalize_phase_gate_summary(manifest.phase_gate_summary)
        phase_gate_fields = phase_gate_flat_fields(manifest.phase_gate_summary)
        manifest.phase_gate_decision = phase_gate_fields.get("phase_gate_decision")  # type: ignore[assignment]
        manifest.phase2_entry_allowed = phase_gate_fields.get("phase2_entry_allowed")  # type: ignore[assignment]
        manifest.phase_gate_reason = phase_gate_fields.get("phase_gate_reason")  # type: ignore[assignment]
        manifest.phase_gate_strict_validation_passed = phase_gate_fields.get(
            "phase_gate_strict_validation_passed"
        )  # type: ignore[assignment]
        manifest.phase_gate_strict_validation_issue_count = phase_gate_fields.get(
            "phase_gate_strict_validation_issue_count"
        )  # type: ignore[assignment]
        manifest.phase_gate_checked_files = phase_gate_fields.get("phase_gate_checked_files")  # type: ignore[assignment]
        manifest.strict_validation_passed = manifest.phase_gate_strict_validation_passed  # type: ignore[assignment]
    if isinstance(manifest.readiness_summary, dict):
        manifest.readiness_summary = normalize_readiness_summary(manifest.readiness_summary)
        readiness_fields = readiness_flat_fields(manifest.readiness_summary)
        manifest.readiness_next_phase_candidate = readiness_fields.get(
            "readiness_next_phase_candidate"
        )  # type: ignore[assignment]
        manifest.readiness_execution_ready = readiness_fields.get("readiness_execution_ready")  # type: ignore[assignment]
    latest_execution_lineage = latest_execution_lineage_fields_from_payload(
        timeline_latest_execution_summary=manifest.timeline_latest_execution_summary,
        timeline_latest_execution_comparison_summary=(
            manifest.timeline_latest_execution_comparison_summary
        ),
        bundle_history_latest_execution_summary=(manifest.bundle_history_latest_execution_summary),
        bundle_history_latest_execution_comparison_summary=(
            manifest.bundle_history_latest_execution_comparison_summary
        ),
        cycle_history_latest_execution_summary=manifest.cycle_history_latest_execution_summary,
        cycle_history_latest_execution_comparison_summary=(
            manifest.cycle_history_latest_execution_comparison_summary
        ),
    )
    apply_latest_execution_lineage(manifest, latest_execution_lineage)
    if isinstance(manifest.execution_summary, dict):
        manifest.execution_summary = normalize_execution_snapshot_summary(
            manifest.execution_summary
        )
    if isinstance(manifest.execution_comparison_summary, dict):
        manifest.execution_comparison_summary = normalize_execution_comparison_summary(
            manifest.execution_comparison_summary
        )
    if isinstance(manifest.execution_diagnostics_summary, dict):
        manifest.execution_diagnostics_summary = normalize_execution_diagnostics_summary(
            manifest.execution_diagnostics_summary
        )
    if isinstance(manifest.execution_gap_history_summary, dict):
        manifest.execution_gap_history_summary = normalize_execution_gap_history_summary(
            manifest.execution_gap_history_summary
        )
    if isinstance(manifest.execution_state_comparison_summary, dict):
        manifest.execution_state_comparison_summary = normalize_execution_state_comparison_summary(
            manifest.execution_state_comparison_summary
        )
    if isinstance(manifest.execution_snapshot_drift_summary, dict):
        manifest.execution_snapshot_drift_summary = normalize_execution_snapshot_drift_summary(
            manifest.execution_snapshot_drift_summary
        )
    if isinstance(manifest.execution_drift_overview_summary, dict):
        manifest.execution_drift_overview_summary = normalize_execution_drift_overview_summary(
            manifest.execution_drift_overview_summary
        )
        execution_drift_fields = execution_drift_overview_flat_fields(
            manifest.execution_drift_overview_summary
        )
        manifest.execution_drift_overview_status = execution_drift_fields.get(
            "execution_drift_overview_status"
        )  # type: ignore[assignment]
        manifest.execution_drift_overview_diagnostics_alignment_match = execution_drift_fields.get(
            "execution_drift_overview_diagnostics_alignment_match"
        )  # type: ignore[assignment]
        manifest.execution_drift_overview_state_comparison_mismatching_count = (
            execution_drift_fields.get(
                "execution_drift_overview_state_comparison_mismatching_count"
            )
        )  # type: ignore[assignment]
        manifest.execution_drift_overview_snapshot_drift_mismatching_snapshot_count = (
            execution_drift_fields.get(
                "execution_drift_overview_snapshot_drift_mismatching_snapshot_count"
            )
        )  # type: ignore[assignment]
    tmp_path.write_text(
        json.dumps(manifest.model_dump(mode="json"), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    tmp_path.replace(path)


def step_for(manifest: LiveEvidenceManifest, name: str) -> StepRecord:
    for step in manifest.steps:
        if step.name == name:
            return step
    step = StepRecord(name=name)
    manifest.steps.append(step)
    if name not in manifest.step_order:
        manifest.step_order.append(name)
    return step


def terminal_outcome(status: str | RunOutcome) -> bool:
    try:
        outcome = RunOutcome(status)
    except ValueError:
        return False
    return outcome in TERMINAL_RUN_OUTCOMES
