from __future__ import annotations

from pathlib import Path

from sis.live_evidence_manifest import (
    LiveEvidenceManifest,
    RunOutcome,
    StepOutcome,
    default_manifest_path,
    load_manifest,
    step_for,
    terminal_outcome,
    write_manifest,
)


def test_live_evidence_manifest_paths_and_terminal_outcomes() -> None:
    assert default_manifest_path("20260522_2308") == Path(
        "logs/live_evidence/manifests/live_evidence_20260522_2308.json"
    )
    assert terminal_outcome(RunOutcome.COMPLETED)
    assert terminal_outcome("completed_with_retries")
    assert terminal_outcome("failed_collection")
    assert not terminal_outcome(RunOutcome.RUNNING)
    assert not terminal_outcome("unknown")


def test_live_evidence_manifest_write_load_normalizes_flat_fields(tmp_path: Path) -> None:
    path = tmp_path / "manifests/live_evidence_20260522_2308.json"
    manifest = LiveEvidenceManifest(
        run_id="20260522_2308",
        status=RunOutcome.COMPLETED_WITH_RETRIES,
        duration_minutes=120,
        metadata_interval_seconds=120,
        phase_gate_summary={
            "decision": "CONDITIONAL_GO_NEEDS_LIVE_WINDOW",
            "phase2_entry_allowed": False,
            "phase2_entry_reason": "Need live window",
            "strict_validation_passed": False,
            "strict_validation_issue_count": 2,
            "checked_files": 7,
        },
        readiness_summary={"next_phase_candidate": "Stay Phase 1", "execution_ready": False},
        timeline_latest_execution_summary={"overall_status": "pass", "venue_count": 2},
        timeline_latest_execution_comparison_summary={"all_registries_present": True},
        execution_drift_overview_summary={
            "overall_status": "degraded",
            "diagnostics_alignment_match": False,
            "state_comparison_mismatching_count": 1,
            "snapshot_drift_mismatching_snapshot_count": 2,
        },
    )

    write_manifest(path, manifest)
    loaded = load_manifest(path)

    assert loaded.run_id == "20260522_2308"
    assert loaded.status == RunOutcome.COMPLETED_WITH_RETRIES
    assert loaded.phase_gate_decision == "CONDITIONAL_GO_NEEDS_LIVE_WINDOW"
    assert loaded.phase2_entry_allowed is False
    assert loaded.phase_gate_reason == "Need live window"
    assert loaded.phase_gate_strict_validation_passed is False
    assert loaded.phase_gate_strict_validation_issue_count == 2
    assert loaded.phase_gate_checked_files == 7
    assert loaded.strict_validation_passed is False
    assert loaded.readiness_next_phase_candidate == "Stay Phase 1"
    assert loaded.readiness_execution_ready is False
    assert loaded.timeline_latest_execution_overall_status == "pass"
    assert loaded.timeline_latest_execution_venue_count == 2
    assert loaded.timeline_latest_execution_comparison_all_registries_present is True
    assert loaded.execution_drift_overview_status == "degraded"
    assert loaded.execution_drift_overview_diagnostics_alignment_match is False
    assert loaded.execution_drift_overview_state_comparison_mismatching_count == 1
    assert loaded.execution_drift_overview_snapshot_drift_mismatching_snapshot_count == 2


def test_step_for_creates_and_reuses_manifest_steps() -> None:
    manifest = LiveEvidenceManifest(
        run_id="20260522_2308",
        duration_minutes=120,
        metadata_interval_seconds=120,
    )

    first = step_for(manifest, "preflight")
    first.status = StepOutcome.RUNNING
    second = step_for(manifest, "preflight")

    assert first is second
    assert second.status == StepOutcome.RUNNING
    assert manifest.step_order == ["preflight"]
