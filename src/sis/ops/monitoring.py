from __future__ import annotations

from pathlib import Path

import polars as pl

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
    normalize_phase_gate_summary,
    normalize_readiness_summary,
    phase_gate_flat_fields,
    readiness_flat_fields,
)
from sis.storage.jsonl_store import read_json, read_jsonl, write_json


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
    phase_gate_summary_path: Path | None = None,
    execution_drift_overview_summary_path: Path | None = None,
    readiness_summary_path: Path | None = None,
    last_healthcheck: dict | None = None,
) -> dict:
    snapshot = {
        "decision_summary_exists": bool(decision_summary_path and decision_summary_path.exists()),
        "weekly_review_exists": bool(weekly_review_path and weekly_review_path.exists()),
        "daily_pnl_exists": bool(daily_pnl_path and daily_pnl_path.exists()),
        "operation_chain_exists": bool(operation_chain_path and operation_chain_path.exists()),
        "last_healthcheck": last_healthcheck or {},
    }
    if decision_summary_path and decision_summary_path.exists():
        payload = read_json(decision_summary_path)
        if isinstance(payload, dict):
            snapshot["decision_summary"] = payload
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
    if execution_snapshot_summary_path and execution_snapshot_summary_path.exists():
        payload = read_json(execution_snapshot_summary_path)
        if isinstance(payload, dict):
            payload = normalize_execution_snapshot_summary(payload)
            snapshot["execution_snapshot"] = payload
            snapshot.update(execution_snapshot_flat_fields(payload))
    if execution_venue_comparison_summary_path and execution_venue_comparison_summary_path.exists():
        payload = read_json(execution_venue_comparison_summary_path)
        if isinstance(payload, dict):
            payload = normalize_execution_comparison_summary(payload)
            snapshot["execution_comparison"] = payload
            snapshot.update(execution_comparison_flat_fields(payload))
    if execution_venue_diagnostics_summary_path and execution_venue_diagnostics_summary_path.exists():
        payload = read_json(execution_venue_diagnostics_summary_path)
        if isinstance(payload, dict):
            payload = normalize_execution_diagnostics_summary(payload)
            snapshot["execution_diagnostics"] = payload
            snapshot.update(execution_diagnostics_flat_fields(payload))
    if execution_gap_history_summary_path and execution_gap_history_summary_path.exists():
        payload = read_json(execution_gap_history_summary_path)
        if isinstance(payload, dict):
            payload = normalize_execution_gap_history_summary(payload)
            snapshot["execution_gap_history"] = payload
            snapshot.update(execution_gap_history_flat_fields(payload))
    if (
        execution_state_comparison_history_summary_path
        and execution_state_comparison_history_summary_path.exists()
    ):
        payload = read_json(execution_state_comparison_history_summary_path)
        if isinstance(payload, dict):
            payload = normalize_execution_state_comparison_summary(payload)
            snapshot["execution_state_comparison"] = payload
            snapshot.update(execution_state_comparison_flat_fields(payload))
    if execution_snapshot_drift_history_summary_path and execution_snapshot_drift_history_summary_path.exists():
        payload = read_json(execution_snapshot_drift_history_summary_path)
        if isinstance(payload, dict):
            payload = normalize_execution_snapshot_drift_summary(payload)
            snapshot["execution_snapshot_drift"] = payload
            snapshot.update(execution_snapshot_drift_flat_fields(payload))
    if audit_dashboard_summary_path and audit_dashboard_summary_path.exists():
        payload = read_json(audit_dashboard_summary_path)
        if isinstance(payload, dict):
            snapshot["audit_dashboard"] = payload
            audit_summary = audit_summary_fields(payload, snapshot.get("audit_bundle"))
            snapshot["audit_summary"] = audit_summary
            snapshot.update(audit_summary)
    if audit_bundle_summary_path and audit_bundle_summary_path.exists():
        payload = read_json(audit_bundle_summary_path)
        if isinstance(payload, dict):
            snapshot["audit_bundle"] = payload
            audit_summary = audit_summary_fields(snapshot.get("audit_dashboard"), payload)
            snapshot["audit_summary"] = audit_summary
            snapshot.update(audit_summary)
    if phase_gate_summary_path and phase_gate_summary_path.exists():
        payload = read_json(phase_gate_summary_path)
        if isinstance(payload, dict):
            payload = normalize_phase_gate_summary(payload)
            snapshot["phase_gate"] = payload
            snapshot["phase_gate_summary"] = payload
            snapshot.update(phase_gate_flat_fields(payload))
    if execution_drift_overview_summary_path and execution_drift_overview_summary_path.exists():
        payload = read_json(execution_drift_overview_summary_path)
        if isinstance(payload, dict):
            payload = normalize_execution_drift_overview_summary(payload)
            snapshot["execution_drift_overview"] = payload
            snapshot["execution_drift_overview_summary"] = payload
            snapshot.update(execution_drift_overview_flat_fields(payload))
    if readiness_summary_path and readiness_summary_path.exists():
        payload = read_json(readiness_summary_path)
        if isinstance(payload, dict):
            payload = normalize_readiness_summary(payload)
            snapshot["readiness"] = payload
            snapshot["readiness_summary"] = payload
            snapshot.update(readiness_flat_fields(payload))
    snapshot["status"] = "ok" if snapshot["decision_summary_exists"] else "degraded"
    return snapshot


def write_monitoring_snapshot(path: Path, snapshot: dict) -> Path:
    write_json(path, snapshot)
    return path
