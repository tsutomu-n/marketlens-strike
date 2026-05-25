from __future__ import annotations

from pathlib import Path

from sis.ops.kill_switch import KillSwitch
from sis.reports.loaders import normalized_summary, safe_read_json_dict
from sis.reports.summary_normalizers import (
    audit_summary_fields,
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
    merged_latest_execution_lineage_fields,
    phase_gate_flat_fields,
    readiness_flat_fields,
)


def build_healthcheck(
    *,
    kill_switch: KillSwitch,
    decision_summary_path: Path | None = None,
    audit_dashboard_summary_path: Path | None = None,
    audit_bundle_summary_path: Path | None = None,
    operations_bundle_manifest_path: Path | None = None,
    phase_gate_summary_path: Path | None = None,
    execution_summary_path: Path | None = None,
    execution_comparison_summary_path: Path | None = None,
    execution_diagnostics_summary_path: Path | None = None,
    execution_gap_history_summary_path: Path | None = None,
    execution_state_comparison_summary_path: Path | None = None,
    execution_snapshot_drift_summary_path: Path | None = None,
    execution_drift_overview_summary_path: Path | None = None,
    readiness_summary_path: Path | None = None,
    reconciliation_store_present: bool = False,
) -> dict:
    audit_dashboard = safe_read_json_dict(audit_dashboard_summary_path)
    audit_bundle = safe_read_json_dict(audit_bundle_summary_path)
    operations_bundle = safe_read_json_dict(operations_bundle_manifest_path)
    phase_gate = normalized_summary(phase_gate_summary_path, normalize_phase_gate_summary)
    execution_summary = normalized_summary(execution_summary_path, normalize_execution_snapshot_summary)
    execution_comparison = normalized_summary(
        execution_comparison_summary_path,
        normalize_execution_comparison_summary,
    )
    execution_diagnostics = normalized_summary(
        execution_diagnostics_summary_path,
        normalize_execution_diagnostics_summary,
    )
    execution_gap_history = normalized_summary(
        execution_gap_history_summary_path,
        normalize_execution_gap_history_summary,
    )
    execution_state_comparison = normalized_summary(
        execution_state_comparison_summary_path,
        normalize_execution_state_comparison_summary,
    )
    execution_snapshot_drift = normalized_summary(
        execution_snapshot_drift_summary_path,
        normalize_execution_snapshot_drift_summary,
    )
    execution_drift_overview = normalized_summary(
        execution_drift_overview_summary_path,
        normalize_execution_drift_overview_summary,
    )
    readiness = normalized_summary(readiness_summary_path, normalize_readiness_summary)
    audit_summary = audit_summary_fields(audit_dashboard, audit_bundle)
    latest_execution_lineage = merged_latest_execution_lineage_fields(
        audit_dashboard,
        audit_bundle,
        operations_bundle,
    )
    return {
        "kill_switch_enabled": kill_switch.is_enabled(),
        "decision_summary_exists": bool(decision_summary_path and decision_summary_path.exists()),
        "audit_summary": audit_summary,
        **latest_execution_lineage,
        "phase_gate_summary": phase_gate,
        "execution_summary": execution_summary,
        "execution_comparison_summary": execution_comparison,
        "execution_diagnostics_summary": execution_diagnostics,
        "execution_gap_history_summary": execution_gap_history,
        "execution_state_comparison_summary": execution_state_comparison,
        "execution_snapshot_drift_summary": execution_snapshot_drift,
        "execution_drift_overview_summary": execution_drift_overview,
        "readiness_summary": readiness,
        **audit_summary,
        **phase_gate_flat_fields(phase_gate),
        **execution_snapshot_flat_fields(execution_summary),
        **execution_comparison_flat_fields(execution_comparison),
        **execution_diagnostics_flat_fields(execution_diagnostics),
        **execution_gap_history_flat_fields(execution_gap_history),
        **execution_state_comparison_flat_fields(execution_state_comparison),
        **execution_snapshot_drift_flat_fields(execution_snapshot_drift),
        **execution_drift_overview_flat_fields(execution_drift_overview),
        **readiness_flat_fields(readiness),
        "reconciliation_store_present": reconciliation_store_present,
        "status": "degraded" if kill_switch.is_enabled() else "ok",
    }
