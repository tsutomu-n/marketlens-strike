from __future__ import annotations

from pathlib import Path

from sis.reports.audit_dashboard_navigation import quick_navigation as _quick_navigation
from sis.reports.audit_dashboard_navigation import related_reports as _related_reports
from sis.reports.audit_dashboard_sections import (
    audit_coverage_section_lines as _audit_coverage_section_lines,
    artifact_summaries_section_lines as _artifact_summaries_section_lines,
    strict_validation_preview_section_lines as _strict_validation_preview_section_lines,
)
from sis.reports.audit_dashboard_sections import overall_section_lines as _overall_section_lines
from sis.reports.loaders import normalized_summary, safe_read_json_dict
from sis.reports.summary_normalizers import (
    audit_summary_fields,
    audit_bundle_history_flat_fields,
    audit_timeline_flat_fields,
    execution_comparison_flat_fields,
    execution_diagnostics_flat_fields,
    execution_gap_history_flat_fields,
    execution_snapshot_flat_fields,
    execution_snapshot_drift_flat_fields,
    execution_state_comparison_flat_fields,
    execution_drift_overview_flat_fields,
    normalize_execution_comparison_summary,
    normalize_execution_diagnostics_summary,
    normalize_execution_gap_history_summary,
    normalize_execution_snapshot_drift_summary,
    normalize_execution_snapshot_summary,
    normalize_execution_state_comparison_summary,
    normalize_execution_drift_overview_summary,
    merged_remapped_latest_execution_lineage_fields,
    normalize_phase_gate_summary,
    normalize_readiness_summary,
    phase_gate_flat_fields,
    readiness_flat_fields,
)
from sis.storage.jsonl_store import write_json


def build_audit_dashboard(
    *,
    bundle_manifest_path: Path | None = None,
    audit_pack_path: Path | None = None,
    audit_timeline_summary_path: Path | None = None,
    audit_bundle_history_summary_path: Path | None = None,
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
    summary_path: Path | None = None,
) -> str:
    bundle = safe_read_json_dict(bundle_manifest_path)
    audit_pack = safe_read_json_dict(audit_pack_path)
    audit_timeline = safe_read_json_dict(audit_timeline_summary_path)
    audit_bundle_history = safe_read_json_dict(audit_bundle_history_summary_path)
    execution = normalized_summary(
        execution_snapshot_summary_path, normalize_execution_snapshot_summary
    )
    execution_comparison = normalized_summary(
        execution_venue_comparison_summary_path,
        normalize_execution_comparison_summary,
    )
    execution_diagnostics = normalized_summary(
        execution_venue_diagnostics_summary_path,
        normalize_execution_diagnostics_summary,
    )
    execution_gap_history = normalized_summary(
        execution_gap_history_summary_path,
        normalize_execution_gap_history_summary,
    )
    execution_state_comparison = normalized_summary(
        execution_state_comparison_history_summary_path,
        normalize_execution_state_comparison_summary,
    )
    execution_snapshot_drift = normalized_summary(
        execution_snapshot_drift_history_summary_path,
        normalize_execution_snapshot_drift_summary,
    )
    execution_drift_overview = normalized_summary(
        execution_drift_overview_summary_path,
        normalize_execution_drift_overview_summary,
    )
    readiness = normalized_summary(readiness_summary_path, normalize_readiness_summary)
    phase_gate = normalized_summary(phase_gate_summary_path, normalize_phase_gate_summary)
    execution_snapshot_fields = execution_snapshot_flat_fields(execution)
    execution_comparison_fields = execution_comparison_flat_fields(execution_comparison)
    execution_diagnostics_fields = execution_diagnostics_flat_fields(execution_diagnostics)
    execution_gap_history_fields = execution_gap_history_flat_fields(execution_gap_history)
    execution_state_comparison_fields = execution_state_comparison_flat_fields(
        execution_state_comparison
    )
    execution_snapshot_drift_fields = execution_snapshot_drift_flat_fields(execution_snapshot_drift)
    execution_drift_fields = execution_drift_overview_flat_fields(execution_drift_overview)
    audit_timeline_fields = audit_timeline_flat_fields(audit_timeline)
    audit_bundle_history_fields = audit_bundle_history_flat_fields(audit_bundle_history)
    audit_summary = audit_summary_fields(audit_pack, audit_bundle_history)
    readiness_fields = readiness_flat_fields(readiness)
    phase_gate_fields = phase_gate_flat_fields(phase_gate)
    latest_execution_lineage = merged_remapped_latest_execution_lineage_fields(
        (audit_timeline, "timeline_latest"),
        (audit_bundle_history, "bundle_history_latest"),
    )
    operation_counts = audit_timeline.get("operation_counts")
    if not isinstance(operation_counts, dict):
        operation_counts = {}

    summary = {
        "overall_status": audit_pack.get("overall_status")
        or bundle.get("overall_status")
        or audit_timeline.get("latest_status"),
        "bundle_status": bundle.get("overall_status"),
        "audit_pack_status": audit_pack.get("overall_status"),
        **latest_execution_lineage,
        **audit_timeline_fields,
        "operations_snapshot_count": operation_counts.get("operations_snapshot"),
        "operations_audit_snapshot_count": operation_counts.get("operations_audit_snapshot"),
        "audit_bundle_snapshot_count": operation_counts.get("audit_bundle_snapshot"),
        "cycle_count": audit_pack.get("cycle_count") or bundle.get("cycle_count"),
        "completed_cycle_count": audit_pack.get("completed_cycle_count")
        or bundle.get("completed_cycle_count"),
        "audit_summary": audit_summary,
        "phase_gate_summary": phase_gate,
        "readiness_summary": readiness,
        **audit_bundle_history_fields,
        "execution_summary": execution,
        "execution_comparison_summary": execution_comparison,
        "execution_diagnostics_summary": execution_diagnostics,
        "execution_gap_history_summary": execution_gap_history,
        "execution_state_comparison_summary": execution_state_comparison,
        "execution_snapshot_drift_summary": execution_snapshot_drift,
        "execution_drift_overview_summary": execution_drift_overview,
        **execution_snapshot_fields,
        **execution_comparison_fields,
        **execution_diagnostics_fields,
        **execution_gap_history_fields,
        **execution_state_comparison_fields,
        **execution_snapshot_drift_fields,
        **execution_drift_fields,
        **readiness_fields,
        **phase_gate_fields,
        "phase_gate_summary_path": str(phase_gate_summary_path)
        if phase_gate_summary_path
        else None,
        "audit_dashboard_report_path": str(out_path) if out_path is not None else None,
        "artifacts": {
            "bundle_manifest": str(bundle_manifest_path) if bundle_manifest_path else None,
            "audit_pack": str(audit_pack_path) if audit_pack_path else None,
            "audit_timeline_summary": str(audit_timeline_summary_path)
            if audit_timeline_summary_path
            else None,
            "audit_bundle_history_summary": str(audit_bundle_history_summary_path)
            if audit_bundle_history_summary_path
            else None,
            "execution_snapshot_summary": str(execution_snapshot_summary_path)
            if execution_snapshot_summary_path
            else None,
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
                str(execution_gap_history_summary_path)
                if execution_gap_history_summary_path
                else None
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
    quick_navigation = _quick_navigation(summary)
    related_reports = _related_reports(summary)
    artifacts = summary["artifacts"] if isinstance(summary.get("artifacts"), dict) else {}
    summary["quick_navigation"] = quick_navigation
    summary["related_reports"] = related_reports

    lines = [
        "# Audit Dashboard",
        "",
        *_overall_section_lines(summary),
        "## Quick Navigation",
        "",
    ]
    for key, value in quick_navigation.items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            *_audit_coverage_section_lines(summary),
            "## Related Reports",
            "",
        ]
    )
    for key, value in related_reports.items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            *_strict_validation_preview_section_lines(summary),
            *_artifact_summaries_section_lines(artifacts),
        ]
    )

    text = "\n".join(lines).rstrip() + "\n"
    if out_path is not None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text, encoding="utf-8")
    if summary_path is not None:
        write_json(summary_path, summary)
    return text
