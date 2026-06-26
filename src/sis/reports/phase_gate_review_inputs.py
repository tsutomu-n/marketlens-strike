from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from sis.reports.loaders import normalized_summary, safe_read_json_dict
from sis.reports.summary_normalizers import (
    execution_comparison_flat_fields,
    execution_diagnostics_flat_fields,
    execution_gap_history_flat_fields,
    execution_snapshot_flat_fields,
    execution_snapshot_drift_flat_fields,
    execution_state_comparison_flat_fields,
    execution_drift_overview_flat_fields,
    normalize_execution_drift_overview_summary,
)


@dataclass(frozen=True)
class PhaseGateExecutionInputs:
    execution_summary: dict
    execution_comparison: dict
    execution_diagnostics: dict
    execution_gap_history: dict
    execution_state_comparison: dict
    execution_snapshot_drift: dict
    execution_drift_overview: dict
    flat_fields: dict[str, object]


def load_phase_gate_execution_inputs(
    *,
    execution_snapshot_summary_path: Path | None,
    execution_venue_comparison_summary_path: Path | None,
    execution_venue_diagnostics_summary_path: Path | None,
    execution_gap_history_summary_path: Path | None,
    execution_state_comparison_history_summary_path: Path | None,
    execution_snapshot_drift_history_summary_path: Path | None,
    execution_drift_overview_summary_path: Path | None,
) -> PhaseGateExecutionInputs:
    execution_summary = safe_read_json_dict(execution_snapshot_summary_path)
    execution_comparison = safe_read_json_dict(execution_venue_comparison_summary_path)
    execution_diagnostics = safe_read_json_dict(execution_venue_diagnostics_summary_path)
    execution_gap_history = safe_read_json_dict(execution_gap_history_summary_path)
    execution_state_comparison = safe_read_json_dict(
        execution_state_comparison_history_summary_path
    )
    execution_snapshot_drift = safe_read_json_dict(execution_snapshot_drift_history_summary_path)
    execution_drift_overview = normalized_summary(
        execution_drift_overview_summary_path,
        normalize_execution_drift_overview_summary,
    )
    flat_fields = {
        **execution_snapshot_flat_fields(execution_summary),
        **execution_comparison_flat_fields(execution_comparison),
        **execution_diagnostics_flat_fields(execution_diagnostics),
        **execution_gap_history_flat_fields(execution_gap_history),
        **execution_state_comparison_flat_fields(execution_state_comparison),
        **execution_snapshot_drift_flat_fields(execution_snapshot_drift),
        **execution_drift_overview_flat_fields(execution_drift_overview),
    }
    return PhaseGateExecutionInputs(
        execution_summary=execution_summary,
        execution_comparison=execution_comparison,
        execution_diagnostics=execution_diagnostics,
        execution_gap_history=execution_gap_history,
        execution_state_comparison=execution_state_comparison,
        execution_snapshot_drift=execution_snapshot_drift,
        execution_drift_overview=execution_drift_overview,
        flat_fields=flat_fields,
    )
