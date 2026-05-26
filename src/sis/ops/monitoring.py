from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

import polars as pl

from sis.reports.loaders import normalized_summary, safe_read_json_dict
from sis.reports.summary_normalizers import (
    audit_summary_fields,
    execution_comparison_flat_fields,
    execution_diagnostics_flat_fields,
    execution_gap_history_flat_fields,
    execution_snapshot_flat_fields,
    execution_snapshot_drift_flat_fields,
    execution_state_comparison_flat_fields,
    normalize_execution_comparison_summary,
    normalize_execution_diagnostics_summary,
    normalize_execution_gap_history_summary,
    normalize_execution_snapshot_summary,
    normalize_execution_snapshot_drift_summary,
    normalize_execution_state_comparison_summary,
    execution_drift_overview_flat_fields,
    normalize_execution_drift_overview_summary,
    merged_latest_execution_lineage_fields,
    normalize_phase_gate_summary,
    normalize_readiness_summary,
    phase_gate_flat_fields,
    readiness_flat_fields,
)
from sis.storage.jsonl_store import read_jsonl, write_json


def _as_mapping(value: object) -> Mapping[str, Any] | None:
    return value if isinstance(value, Mapping) else None


def build_monitoring_snapshot(
    *,
    decision_summary_path: Path | None = None,
    weekly_review_path: Path | None = None,
    daily_pnl_path: Path | None = None,
    operation_chain_path: Path | None = None,
    execution_snapshot_summary_path: Path | None = None,
    execution_venue_comparison_summary_path: Path | None = None,
    execution_venue_diagnostics_summary_path: Path | None = None,
    execution_gap_history_summary_path: Path | None = None,
    execution_state_comparison_history_summary_path: Path | None = None,
    execution_snapshot_drift_history_summary_path: Path | None = None,
    audit_dashboard_summary_path: Path | None = None,
    audit_bundle_summary_path: Path | None = None,
    operations_bundle_manifest_path: Path | None = None,
    phase_gate_summary_path: Path | None = None,
    execution_drift_overview_summary_path: Path | None = None,
    readiness_summary_path: Path | None = None,
    last_healthcheck: dict | None = None,
) -> dict:
    snapshot: dict[str, object] = {
        "decision_summary_exists": bool(decision_summary_path and decision_summary_path.exists()),
        "weekly_review_exists": bool(weekly_review_path and weekly_review_path.exists()),
        "daily_pnl_exists": bool(daily_pnl_path and daily_pnl_path.exists()),
        "operation_chain_exists": bool(operation_chain_path and operation_chain_path.exists()),
        "last_healthcheck": last_healthcheck or {},
    }
    decision_summary = safe_read_json_dict(decision_summary_path)
    if decision_summary:
        snapshot["decision_summary"] = decision_summary
    if daily_pnl_path and daily_pnl_path.exists():
        pnl = pl.read_parquet(daily_pnl_path)
        snapshot["paper_pnl_rows"] = pnl.height
        if pnl.height and "realized_pnl" in pnl.columns:
            snapshot["paper_total_realized_pnl"] = float(pnl["realized_pnl"].sum())
    if operation_chain_path and operation_chain_path.exists():
        operations = list(read_jsonl(operation_chain_path))
        snapshot["operation_chain_count"] = len(operations)
        if operations:
            snapshot["latest_operation"] = operations[-1]
    execution_snapshot = normalized_summary(
        execution_snapshot_summary_path,
        normalize_execution_snapshot_summary,
    )
    if execution_snapshot:
        snapshot["execution_snapshot"] = execution_snapshot
        snapshot.update(execution_snapshot_flat_fields(execution_snapshot))
    execution_comparison = normalized_summary(
        execution_venue_comparison_summary_path,
        normalize_execution_comparison_summary,
    )
    if execution_comparison:
        snapshot["execution_comparison"] = execution_comparison
        snapshot.update(execution_comparison_flat_fields(execution_comparison))
    execution_diagnostics = normalized_summary(
        execution_venue_diagnostics_summary_path,
        normalize_execution_diagnostics_summary,
    )
    if execution_diagnostics:
        snapshot["execution_diagnostics"] = execution_diagnostics
        snapshot.update(execution_diagnostics_flat_fields(execution_diagnostics))
    execution_gap_history = normalized_summary(
        execution_gap_history_summary_path,
        normalize_execution_gap_history_summary,
    )
    if execution_gap_history:
        snapshot["execution_gap_history"] = execution_gap_history
        snapshot.update(execution_gap_history_flat_fields(execution_gap_history))
    execution_state_comparison = normalized_summary(
        execution_state_comparison_history_summary_path,
        normalize_execution_state_comparison_summary,
    )
    if execution_state_comparison:
        snapshot["execution_state_comparison"] = execution_state_comparison
        snapshot.update(execution_state_comparison_flat_fields(execution_state_comparison))
    execution_snapshot_drift = normalized_summary(
        execution_snapshot_drift_history_summary_path,
        normalize_execution_snapshot_drift_summary,
    )
    if execution_snapshot_drift:
        snapshot["execution_snapshot_drift"] = execution_snapshot_drift
        snapshot.update(execution_snapshot_drift_flat_fields(execution_snapshot_drift))
    audit_dashboard = safe_read_json_dict(audit_dashboard_summary_path)
    if audit_dashboard:
        snapshot["audit_dashboard"] = audit_dashboard
        audit_summary = audit_summary_fields(
            audit_dashboard, _as_mapping(snapshot.get("audit_bundle"))
        )
        snapshot["audit_summary"] = audit_summary
        snapshot.update(audit_summary)
    audit_bundle = safe_read_json_dict(audit_bundle_summary_path)
    if audit_bundle:
        snapshot["audit_bundle"] = audit_bundle
        audit_summary = audit_summary_fields(
            _as_mapping(snapshot.get("audit_dashboard")), audit_bundle
        )
        snapshot["audit_summary"] = audit_summary
        snapshot.update(audit_summary)
    operations_bundle = safe_read_json_dict(operations_bundle_manifest_path)
    if operations_bundle:
        snapshot["operations_bundle"] = operations_bundle
    phase_gate = normalized_summary(
        phase_gate_summary_path,
        normalize_phase_gate_summary,
    )
    if phase_gate:
        snapshot["phase_gate"] = phase_gate
        snapshot["phase_gate_summary"] = phase_gate
        snapshot.update(phase_gate_flat_fields(phase_gate))
    execution_drift_overview = normalized_summary(
        execution_drift_overview_summary_path,
        normalize_execution_drift_overview_summary,
    )
    if execution_drift_overview:
        snapshot["execution_drift_overview"] = execution_drift_overview
        snapshot["execution_drift_overview_summary"] = execution_drift_overview
        snapshot.update(execution_drift_overview_flat_fields(execution_drift_overview))
    readiness = normalized_summary(
        readiness_summary_path,
        normalize_readiness_summary,
    )
    if readiness:
        snapshot["readiness"] = readiness
        snapshot["readiness_summary"] = readiness
        snapshot.update(readiness_flat_fields(readiness))
    snapshot.update(
        merged_latest_execution_lineage_fields(
            _as_mapping(snapshot.get("audit_dashboard")),
            _as_mapping(snapshot.get("audit_bundle")),
            _as_mapping(snapshot.get("operations_bundle")),
        )
    )
    snapshot["status"] = "ok" if snapshot["decision_summary_exists"] else "degraded"
    return snapshot


def write_monitoring_snapshot(path: Path, snapshot: dict) -> Path:
    write_json(path, snapshot)
    return path
