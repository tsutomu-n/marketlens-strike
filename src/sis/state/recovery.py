from __future__ import annotations

from pathlib import Path

from sis.reports.summary_normalizers import (
    audit_summary_fields,
    execution_comparison_flat_fields,
    execution_diagnostics_flat_fields,
    execution_gap_history_flat_fields,
    execution_snapshot_drift_flat_fields,
    execution_snapshot_flat_fields,
    execution_state_comparison_flat_fields,
    execution_drift_overview_flat_fields,
    normalize_execution_comparison_summary,
    normalize_execution_diagnostics_summary,
    normalize_execution_drift_overview_summary,
    normalize_execution_gap_history_summary,
    normalize_execution_snapshot_drift_summary,
    normalize_execution_snapshot_summary,
    normalize_execution_state_comparison_summary,
    phase_gate_flat_fields,
    normalize_phase_gate_summary,
    readiness_flat_fields,
    normalize_readiness_summary,
)
from sis.state.store import StateStore
from sis.storage.jsonl_store import read_json, write_json


def export_state_snapshot(store: StateStore, out_path: Path) -> Path:
    paper_last_run = store.get_json("paper_last_run")
    audit_summary = paper_last_run.get("audit") if isinstance(paper_last_run, dict) else None
    normalized_audit_summary = audit_summary_fields(
        audit_summary if isinstance(audit_summary, dict) else {},
        audit_summary if isinstance(audit_summary, dict) else {},
    )
    phase_gate_summary = paper_last_run.get("phase_gate") if isinstance(paper_last_run, dict) else None
    normalized_phase_gate_summary = normalize_phase_gate_summary(
        phase_gate_summary if isinstance(phase_gate_summary, dict) else {}
    )
    readiness_summary = paper_last_run.get("readiness_summary") if isinstance(paper_last_run, dict) else None
    execution_summary = paper_last_run.get("execution_summary") if isinstance(paper_last_run, dict) else None
    execution_comparison_summary = (
        paper_last_run.get("execution_comparison_summary") if isinstance(paper_last_run, dict) else None
    )
    execution_diagnostics_summary = (
        paper_last_run.get("execution_diagnostics_summary") if isinstance(paper_last_run, dict) else None
    )
    execution_gap_history_summary = (
        paper_last_run.get("execution_gap_history_summary") if isinstance(paper_last_run, dict) else None
    )
    execution_state_comparison_summary = (
        paper_last_run.get("execution_state_comparison_summary") if isinstance(paper_last_run, dict) else None
    )
    execution_snapshot_drift_summary = (
        paper_last_run.get("execution_snapshot_drift_summary") if isinstance(paper_last_run, dict) else None
    )
    execution_drift_overview_summary = (
        paper_last_run.get("execution_drift_overview_summary") if isinstance(paper_last_run, dict) else None
    )
    normalized_readiness_summary = normalize_readiness_summary(
        readiness_summary if isinstance(readiness_summary, dict) else {}
    )
    normalized_execution_summary = normalize_execution_snapshot_summary(
        execution_summary if isinstance(execution_summary, dict) else {}
    )
    normalized_execution_comparison_summary = normalize_execution_comparison_summary(
        execution_comparison_summary if isinstance(execution_comparison_summary, dict) else {}
    )
    normalized_execution_diagnostics_summary = normalize_execution_diagnostics_summary(
        execution_diagnostics_summary if isinstance(execution_diagnostics_summary, dict) else {}
    )
    normalized_execution_gap_history_summary = normalize_execution_gap_history_summary(
        execution_gap_history_summary if isinstance(execution_gap_history_summary, dict) else {}
    )
    normalized_execution_state_comparison_summary = normalize_execution_state_comparison_summary(
        execution_state_comparison_summary if isinstance(execution_state_comparison_summary, dict) else {}
    )
    normalized_execution_snapshot_drift_summary = normalize_execution_snapshot_drift_summary(
        execution_snapshot_drift_summary if isinstance(execution_snapshot_drift_summary, dict) else {}
    )
    normalized_execution_drift_overview_summary = normalize_execution_drift_overview_summary(
        execution_drift_overview_summary if isinstance(execution_drift_overview_summary, dict) else {}
    )
    phase_gate_flat = phase_gate_flat_fields(normalized_phase_gate_summary)
    readiness_flat = readiness_flat_fields(normalized_readiness_summary)
    execution_summary_flat = execution_snapshot_flat_fields(normalized_execution_summary)
    execution_comparison_flat = execution_comparison_flat_fields(
        normalized_execution_comparison_summary
    )
    execution_diagnostics_flat = execution_diagnostics_flat_fields(
        normalized_execution_diagnostics_summary
    )
    execution_gap_history_flat = execution_gap_history_flat_fields(
        normalized_execution_gap_history_summary
    )
    execution_state_comparison_flat = execution_state_comparison_flat_fields(
        normalized_execution_state_comparison_summary
    )
    execution_snapshot_drift_flat = execution_snapshot_drift_flat_fields(
        normalized_execution_snapshot_drift_summary
    )
    execution_drift_flat = execution_drift_overview_flat_fields(
        normalized_execution_drift_overview_summary
    )
    snapshot = {
        "paper_positions": store.get_json("paper_positions"),
        "paper_last_run": paper_last_run,
        "audit_summary": normalized_audit_summary,
        "phase_gate_summary": normalized_phase_gate_summary,
        **phase_gate_flat,
        "readiness_summary": normalized_readiness_summary,
        **readiness_flat,
        "execution_summary": normalized_execution_summary,
        **execution_summary_flat,
        "execution_comparison_summary": normalized_execution_comparison_summary,
        **execution_comparison_flat,
        "execution_diagnostics_summary": normalized_execution_diagnostics_summary,
        **execution_diagnostics_flat,
        "execution_gap_history_summary": normalized_execution_gap_history_summary,
        **execution_gap_history_flat,
        "execution_state_comparison_summary": normalized_execution_state_comparison_summary,
        **execution_state_comparison_flat,
        "execution_snapshot_drift_summary": normalized_execution_snapshot_drift_summary,
        **execution_snapshot_drift_flat,
        "execution_drift_overview_summary": normalized_execution_drift_overview_summary,
        **execution_drift_flat,
        "latest_reconciliation": store.latest_reconciliation(),
    }
    if normalized_audit_summary.get("audit_overall_status") is not None:
        snapshot["audit_overall_status"] = normalized_audit_summary.get("audit_overall_status")
    if normalized_audit_summary.get("audit_latest_operation") is not None:
        snapshot["audit_latest_operation"] = normalized_audit_summary.get("audit_latest_operation")
    if normalized_audit_summary.get("audit_bundle_history_snapshot_count") is not None:
        snapshot["audit_bundle_history_snapshot_count"] = normalized_audit_summary.get(
            "audit_bundle_history_snapshot_count"
        )
    if phase_gate_flat.get("phase_gate_decision") is not None:
        snapshot["phase_gate_decision"] = phase_gate_flat.get("phase_gate_decision")
    if phase_gate_flat.get("phase2_entry_allowed") is not None:
        snapshot["phase2_entry_allowed"] = phase_gate_flat.get("phase2_entry_allowed")
    if phase_gate_flat.get("phase2_entry_reason") is not None:
        snapshot["phase2_entry_reason"] = phase_gate_flat.get("phase2_entry_reason")
    if readiness_flat.get("readiness_next_phase_candidate") is not None:
        snapshot["readiness_next_phase_candidate"] = readiness_flat.get(
            "readiness_next_phase_candidate"
        )
    elif isinstance(paper_last_run, dict) and paper_last_run.get("readiness_next_phase_candidate") is not None:
        snapshot["readiness_next_phase_candidate"] = paper_last_run.get("readiness_next_phase_candidate")
    if readiness_flat.get("readiness_execution_ready") is not None:
        snapshot["readiness_execution_ready"] = readiness_flat.get("readiness_execution_ready")
    elif isinstance(paper_last_run, dict) and paper_last_run.get("readiness_execution_ready") is not None:
        snapshot["readiness_execution_ready"] = paper_last_run.get("readiness_execution_ready")
    if execution_drift_flat.get("execution_drift_overview_status") is not None:
        snapshot["execution_drift_overview_status"] = execution_drift_flat.get(
            "execution_drift_overview_status"
        )
    elif isinstance(paper_last_run, dict) and paper_last_run.get("execution_drift_overview_status") is not None:
        snapshot["execution_drift_overview_status"] = paper_last_run.get("execution_drift_overview_status")
    if (
        execution_drift_flat.get("execution_drift_overview_diagnostics_alignment_match") is not None
    ):
        snapshot["execution_drift_overview_diagnostics_alignment_match"] = execution_drift_flat.get(
            "execution_drift_overview_diagnostics_alignment_match"
        )
    elif (
        isinstance(paper_last_run, dict)
        and paper_last_run.get("execution_drift_overview_diagnostics_alignment_match") is not None
    ):
        snapshot["execution_drift_overview_diagnostics_alignment_match"] = paper_last_run.get(
            "execution_drift_overview_diagnostics_alignment_match"
        )
    if (
        execution_drift_flat.get("execution_drift_overview_state_comparison_mismatching_count")
        is not None
    ):
        snapshot["execution_drift_overview_state_comparison_mismatching_count"] = (
            execution_drift_flat.get("execution_drift_overview_state_comparison_mismatching_count")
        )
    elif (
        isinstance(paper_last_run, dict)
        and paper_last_run.get("execution_drift_overview_state_comparison_mismatching_count") is not None
    ):
        snapshot["execution_drift_overview_state_comparison_mismatching_count"] = paper_last_run.get(
            "execution_drift_overview_state_comparison_mismatching_count"
        )
    if (
        execution_drift_flat.get(
            "execution_drift_overview_snapshot_drift_mismatching_snapshot_count"
        )
        is not None
    ):
        snapshot["execution_drift_overview_snapshot_drift_mismatching_snapshot_count"] = (
            execution_drift_flat.get(
                "execution_drift_overview_snapshot_drift_mismatching_snapshot_count"
            )
        )
    elif (
        isinstance(paper_last_run, dict)
        and paper_last_run.get("execution_drift_overview_snapshot_drift_mismatching_snapshot_count") is not None
    ):
        snapshot["execution_drift_overview_snapshot_drift_mismatching_snapshot_count"] = paper_last_run.get(
            "execution_drift_overview_snapshot_drift_mismatching_snapshot_count"
        )
    write_json(out_path, snapshot)
    return out_path


def restore_state_snapshot(store: StateStore, snapshot_path: Path) -> None:
    payload = read_json(snapshot_path)
    if not isinstance(payload, dict):
        raise ValueError("State snapshot payload must be an object")
    if "paper_positions" in payload:
        store.set_json("paper_positions", payload["paper_positions"])
    if "paper_last_run" in payload:
        store.set_json("paper_last_run", payload["paper_last_run"])
