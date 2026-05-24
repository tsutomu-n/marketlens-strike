from __future__ import annotations

from pathlib import Path

from sis.reports.summary_normalizers import (
    audit_timeline_flat_fields,
    execution_comparison_flat_fields,
    execution_diagnostics_flat_fields,
    execution_gap_history_flat_fields,
    execution_snapshot_flat_fields,
    execution_snapshot_drift_flat_fields,
    execution_state_comparison_flat_fields,
    execution_drift_overview_flat_fields,
    normalize_execution_drift_overview_summary,
    normalize_phase_gate_summary,
    normalize_readiness_summary,
    phase_gate_flat_fields,
    phase_gate_issue_preview_lines,
    readiness_flat_fields,
)
from sis.storage.jsonl_store import read_json, write_json


def _safe_read_json(path: Path | None) -> dict:
    if path is None or not path.exists():
        return {}
    payload = read_json(path)
    return payload if isinstance(payload, dict) else {}


def build_operations_audit_pack(
    *,
    bundle_manifest_path: Path | None = None,
    timeline_summary_path: Path | None = None,
    cycle_history_summary_path: Path | None = None,
    runbook_summary_path: Path | None = None,
    execution_snapshot_summary_path: Path | None = None,
    execution_venue_comparison_summary_path: Path | None = None,
    execution_venue_diagnostics_summary_path: Path | None = None,
    execution_gap_history_summary_path: Path | None = None,
    execution_state_comparison_history_summary_path: Path | None = None,
    execution_snapshot_drift_history_summary_path: Path | None = None,
    execution_drift_overview_summary_path: Path | None = None,
    readiness_summary_path: Path | None = None,
    phase_gate_summary_path: Path | None = None,
    out_path: Path | None = None,
    manifest_path: Path | None = None,
) -> str:
    bundle = _safe_read_json(bundle_manifest_path)
    timeline = _safe_read_json(timeline_summary_path)
    cycle_history = _safe_read_json(cycle_history_summary_path)
    runbook = _safe_read_json(runbook_summary_path)
    execution = _safe_read_json(execution_snapshot_summary_path)
    execution_comparison = _safe_read_json(execution_venue_comparison_summary_path)
    execution_diagnostics = _safe_read_json(execution_venue_diagnostics_summary_path)
    execution_gap_history = _safe_read_json(execution_gap_history_summary_path)
    execution_state_comparison = _safe_read_json(execution_state_comparison_history_summary_path)
    execution_snapshot_drift = _safe_read_json(execution_snapshot_drift_history_summary_path)
    execution_drift_overview = normalize_execution_drift_overview_summary(
        _safe_read_json(execution_drift_overview_summary_path)
    )
    readiness = normalize_readiness_summary(_safe_read_json(readiness_summary_path))
    phase_gate = normalize_phase_gate_summary(_safe_read_json(phase_gate_summary_path))
    execution_snapshot_fields = execution_snapshot_flat_fields(execution)
    execution_comparison_fields = execution_comparison_flat_fields(execution_comparison)
    execution_diagnostics_fields = execution_diagnostics_flat_fields(execution_diagnostics)
    execution_gap_history_fields = execution_gap_history_flat_fields(execution_gap_history)
    execution_state_comparison_fields = execution_state_comparison_flat_fields(
        execution_state_comparison
    )
    execution_snapshot_drift_fields = execution_snapshot_drift_flat_fields(
        execution_snapshot_drift
    )
    execution_drift_fields = execution_drift_overview_flat_fields(execution_drift_overview)
    timeline_fields = audit_timeline_flat_fields(timeline)
    readiness_fields = readiness_flat_fields(readiness)
    phase_gate_fields = phase_gate_flat_fields(phase_gate)

    manifest = {
        "overall_status": bundle.get("overall_status"),
        **timeline_fields,
        "cycle_count": cycle_history.get("cycle_count"),
        "completed_cycle_count": cycle_history.get("completed_count"),
        "runbook_monitoring_status": runbook.get("monitoring_status"),
        **execution_snapshot_fields,
        **execution_comparison_fields,
        **execution_diagnostics_fields,
        **execution_gap_history_fields,
        **execution_state_comparison_fields,
        **execution_snapshot_drift_fields,
        **execution_drift_fields,
        **readiness_fields,
        **phase_gate_fields,
        "artifacts": {
            "bundle_manifest": str(bundle_manifest_path) if bundle_manifest_path else None,
            "timeline_summary": str(timeline_summary_path) if timeline_summary_path else None,
            "cycle_history_summary": str(cycle_history_summary_path) if cycle_history_summary_path else None,
            "runbook_summary": str(runbook_summary_path) if runbook_summary_path else None,
            "execution_snapshot_summary": str(execution_snapshot_summary_path) if execution_snapshot_summary_path else None,
            "execution_venue_comparison_summary": (
                str(execution_venue_comparison_summary_path)
                if execution_venue_comparison_summary_path
                else None
            ),
            "execution_venue_diagnostics_summary": (
                str(execution_venue_diagnostics_summary_path)
                if execution_venue_diagnostics_summary_path
                else None
            ),
            "execution_gap_history_summary": (
                str(execution_gap_history_summary_path) if execution_gap_history_summary_path else None
            ),
            "execution_state_comparison_history_summary": (
                str(execution_state_comparison_history_summary_path)
                if execution_state_comparison_history_summary_path
                else None
            ),
            "execution_snapshot_drift_history_summary": (
                str(execution_snapshot_drift_history_summary_path)
                if execution_snapshot_drift_history_summary_path
                else None
            ),
            "execution_drift_overview_summary": (
                str(execution_drift_overview_summary_path)
                if execution_drift_overview_summary_path
                else None
            ),
            "readiness_summary": str(readiness_summary_path) if readiness_summary_path else None,
            "phase_gate_summary": str(phase_gate_summary_path) if phase_gate_summary_path else None,
        },
    }

    lines = [
        "# Operations Audit Pack",
        "",
        "## Audit Summary",
        "",
        f"- overall_status: {manifest['overall_status']}",
        f"- timeline_latest_operation: {manifest['timeline_latest_operation']}",
        f"- timeline_latest_status: {manifest['timeline_latest_status']}",
        f"- timeline_latest_execution_gap_history_status: {manifest['timeline_latest_execution_gap_history_status']}",
        (
            "- timeline_latest_execution_gap_history_diagnostics_status: "
            f"{manifest['timeline_latest_execution_gap_history_diagnostics_status']}"
        ),
        f"- timeline_latest_readiness_execution_ready: {manifest['timeline_latest_readiness_execution_ready']}",
        f"- cycle_count: {manifest['cycle_count']}",
        f"- completed_cycle_count: {manifest['completed_cycle_count']}",
        f"- runbook_monitoring_status: {manifest['runbook_monitoring_status']}",
        f"- execution_overall_status: {manifest['execution_overall_status']}",
        f"- execution_venue_count: {manifest['execution_venue_count']}",
        f"- execution_comparison_all_registries_present: {manifest['execution_comparison_all_registries_present']}",
        f"- execution_diagnostics_status: {manifest['execution_diagnostics_status']}",
        f"- execution_balance_gap_detected: {manifest['execution_balance_gap_detected']}",
        f"- execution_fills_gap_detected: {manifest['execution_fills_gap_detected']}",
        f"- execution_gap_history_entry_count: {manifest['execution_gap_history_entry_count']}",
        f"- execution_gap_history_latest_status: {manifest['execution_gap_history_latest_status']}",
        f"- execution_gap_history_latest_diagnostics_status: {manifest['execution_gap_history_latest_diagnostics_status']}",
        f"- execution_state_comparison_entry_count: {manifest['execution_state_comparison_entry_count']}",
        (
            "- execution_state_comparison_latest_status_match: "
            f"{manifest['execution_state_comparison_latest_status_match']}"
        ),
        (
            "- execution_state_comparison_mismatching_count: "
            f"{manifest['execution_state_comparison_mismatching_count']}"
        ),
        f"- execution_snapshot_drift_entry_count: {manifest['execution_snapshot_drift_entry_count']}",
        (
            "- execution_snapshot_drift_latest_status_match: "
            f"{manifest['execution_snapshot_drift_latest_status_match']}"
        ),
        (
            "- execution_snapshot_drift_mismatching_snapshot_count: "
            f"{manifest['execution_snapshot_drift_mismatching_snapshot_count']}"
        ),
        f"- execution_drift_overview_status: {manifest['execution_drift_overview_status']}",
        (
            "- execution_drift_overview_diagnostics_alignment_match: "
            f"{manifest['execution_drift_overview_diagnostics_alignment_match']}"
        ),
        (
            "- execution_drift_overview_state_comparison_mismatching_count: "
            f"{manifest['execution_drift_overview_state_comparison_mismatching_count']}"
        ),
        (
            "- execution_drift_overview_snapshot_drift_mismatching_snapshot_count: "
            f"{manifest['execution_drift_overview_snapshot_drift_mismatching_snapshot_count']}"
        ),
        f"- readiness_next_phase_candidate: {manifest['readiness_next_phase_candidate']}",
        f"- readiness_execution_ready: {manifest['readiness_execution_ready']}",
        f"- phase_gate_decision: {manifest['phase_gate_decision']}",
        f"- phase2_entry_allowed: {manifest['phase2_entry_allowed']}",
        f"- phase_gate_reason: {manifest['phase_gate_reason']}",
        f"- phase_gate_strict_validation_passed: {manifest['phase_gate_strict_validation_passed']}",
        f"- phase_gate_strict_validation_issue_count: {manifest['phase_gate_strict_validation_issue_count']}",
        f"- phase_gate_checked_files: {manifest['phase_gate_checked_files']}",
        f"- phase_gate_review_report_path: {manifest['phase_gate_review_report_path']}",
        "",
        "## Strict Validation Preview",
        "",
    ]
    validation_issue_previews = phase_gate_issue_preview_lines(manifest)
    if validation_issue_previews:
        lines.extend(f"- {item}" for item in validation_issue_previews)
    else:
        lines.append("- issues: none")
    lines.extend(
        [
            "",
        "## Included Summaries",
        "",
        ]
    )
    for key, value in manifest["artifacts"].items():
        lines.append(f"- {key}: {value}")
    lines.append("")

    text = "\n".join(lines).rstrip() + "\n"
    if out_path is not None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text, encoding="utf-8")
    if manifest_path is not None:
        write_json(manifest_path, manifest)
    return text
