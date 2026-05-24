from __future__ import annotations

from pathlib import Path

from sis.ops.kill_switch import KillSwitch
from sis.reports.summary_normalizers import (
    audit_summary_fields,
    execution_drift_overview_flat_fields,
    normalize_execution_drift_overview_summary,
    normalize_phase_gate_summary,
    normalize_readiness_summary,
    phase_gate_flat_fields,
    readiness_flat_fields,
)
from sis.storage.jsonl_store import read_json


def _safe_read_json(path: Path | None) -> dict:
    if path is None or not path.exists():
        return {}
    payload = read_json(path)
    return payload if isinstance(payload, dict) else {}


def build_healthcheck(
    *,
    kill_switch: KillSwitch,
    decision_summary_path: Path | None = None,
    audit_dashboard_summary_path: Path | None = None,
    audit_bundle_summary_path: Path | None = None,
    phase_gate_summary_path: Path | None = None,
    execution_drift_overview_summary_path: Path | None = None,
    readiness_summary_path: Path | None = None,
    reconciliation_store_present: bool = False,
) -> dict:
    audit_dashboard = _safe_read_json(audit_dashboard_summary_path)
    audit_bundle = _safe_read_json(audit_bundle_summary_path)
    phase_gate = normalize_phase_gate_summary(_safe_read_json(phase_gate_summary_path))
    execution_drift_overview = normalize_execution_drift_overview_summary(
        _safe_read_json(execution_drift_overview_summary_path)
    )
    readiness = normalize_readiness_summary(_safe_read_json(readiness_summary_path))
    audit_summary = audit_summary_fields(audit_dashboard, audit_bundle)
    return {
        "kill_switch_enabled": kill_switch.is_enabled(),
        "decision_summary_exists": bool(decision_summary_path and decision_summary_path.exists()),
        "audit_summary": audit_summary,
        "phase_gate_summary": phase_gate,
        "execution_drift_overview_summary": execution_drift_overview,
        "readiness_summary": readiness,
        **audit_summary,
        **phase_gate_flat_fields(phase_gate),
        **execution_drift_overview_flat_fields(execution_drift_overview),
        **readiness_flat_fields(readiness),
        "reconciliation_store_present": reconciliation_store_present,
        "status": "degraded" if kill_switch.is_enabled() else "ok",
    }
