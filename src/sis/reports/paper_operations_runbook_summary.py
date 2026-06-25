from __future__ import annotations

from pathlib import Path

from sis.reports.summary_normalizers import (
    execution_comparison_flat_fields,
    execution_diagnostics_flat_fields,
    execution_drift_overview_flat_fields,
    execution_gap_history_flat_fields,
    execution_snapshot_drift_flat_fields,
    execution_snapshot_flat_fields,
    execution_state_comparison_flat_fields,
    latest_execution_lineage_fields_from_summary,
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


def _path_text(path: Path | None) -> str | None:
    return str(path) if path is not None else None


def build_paper_operations_runbook_base_summary(
    *,
    scheduled_run_path: Path | None,
    daemon_manifest_path: Path | None,
    monitoring_snapshot_path: Path | None,
    execution_snapshot_summary_path: Path | None,
    execution_venue_comparison_summary_path: Path | None,
    execution_venue_diagnostics_summary_path: Path | None,
    execution_gap_history_summary_path: Path | None,
    execution_state_comparison_history_summary_path: Path | None,
    execution_snapshot_drift_history_summary_path: Path | None,
    execution_drift_overview_summary_path: Path | None,
    readiness_summary_path: Path | None,
    phase_gate_summary_path: Path | None,
    ops_dashboard_summary_path: Path | None,
    scheduled_run: dict[str, object],
    daemon_manifest: dict[str, object],
    monitoring: dict[str, object],
    execution: dict[str, object],
    execution_comparison: dict[str, object],
    execution_diagnostics: dict[str, object],
    execution_gap_history: dict[str, object],
    execution_state_comparison: dict[str, object],
    execution_snapshot_drift: dict[str, object],
    execution_drift_overview: dict[str, object],
    readiness: dict[str, object],
    phase_gate: dict[str, object],
    dashboard: dict[str, object],
) -> dict[str, object]:
    execution = normalize_execution_snapshot_summary(execution)
    execution_comparison = normalize_execution_comparison_summary(execution_comparison)
    execution_diagnostics = normalize_execution_diagnostics_summary(execution_diagnostics)
    execution_gap_history = normalize_execution_gap_history_summary(execution_gap_history)
    execution_state_comparison = normalize_execution_state_comparison_summary(
        execution_state_comparison
    )
    execution_snapshot_drift = normalize_execution_snapshot_drift_summary(execution_snapshot_drift)
    execution_drift_overview = normalize_execution_drift_overview_summary(execution_drift_overview)
    readiness = normalize_readiness_summary(readiness)
    phase_gate = normalize_phase_gate_summary(phase_gate)

    return {
        "scheduled_run_type": scheduled_run.get("run_type"),
        "scheduled_for": scheduled_run.get("scheduled_for"),
        "scheduled_command": scheduled_run.get("command"),
        "scheduled_run_path": _path_text(scheduled_run_path),
        "daemon_manifest_path": _path_text(daemon_manifest_path),
        "monitoring_snapshot_path": _path_text(monitoring_snapshot_path),
        "execution_snapshot_summary_path": _path_text(execution_snapshot_summary_path),
        "execution_venue_comparison_summary_path": _path_text(
            execution_venue_comparison_summary_path
        ),
        "execution_venue_diagnostics_summary_path": _path_text(
            execution_venue_diagnostics_summary_path
        ),
        "execution_gap_history_summary_path": _path_text(execution_gap_history_summary_path),
        "execution_state_comparison_history_summary_path": _path_text(
            execution_state_comparison_history_summary_path
        ),
        "execution_snapshot_drift_history_summary_path": _path_text(
            execution_snapshot_drift_history_summary_path
        ),
        "execution_drift_overview_summary_path": _path_text(execution_drift_overview_summary_path),
        "readiness_summary_path": _path_text(readiness_summary_path),
        "phase_gate_summary_path": _path_text(phase_gate_summary_path),
        "ops_dashboard_summary_path": _path_text(ops_dashboard_summary_path),
        "daemon_mode": daemon_manifest.get("mode"),
        "monitoring_status": monitoring.get("status"),
        "phase_gate_summary": phase_gate,
        "readiness_summary": readiness,
        "execution_summary": execution,
        "execution_comparison_summary": execution_comparison,
        "execution_diagnostics_summary": execution_diagnostics,
        "execution_gap_history_summary": execution_gap_history,
        "execution_state_comparison_summary": execution_state_comparison,
        "execution_snapshot_drift_summary": execution_snapshot_drift,
        "execution_drift_overview_summary": execution_drift_overview,
        **latest_execution_lineage_fields_from_summary(dashboard),
        **execution_snapshot_flat_fields(execution),
        **execution_comparison_flat_fields(execution_comparison),
        **execution_diagnostics_flat_fields(execution_diagnostics),
        **execution_gap_history_flat_fields(execution_gap_history),
        **execution_state_comparison_flat_fields(execution_state_comparison),
        **execution_snapshot_drift_flat_fields(execution_snapshot_drift),
        **execution_drift_overview_flat_fields(execution_drift_overview),
        **readiness_flat_fields(readiness),
        **phase_gate_flat_fields(phase_gate),
        **{
            key: value
            for key, value in dashboard.items()
            if isinstance(key, str) and key.startswith("timeline_latest_remediation_")
        },
        "dashboard_status": dashboard.get("overall_status"),
    }
