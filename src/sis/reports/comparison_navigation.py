from __future__ import annotations

from pathlib import Path
from typing import Any, cast

from sis.reports.summary_normalizers import (
    execution_comparison_flat_fields,
    execution_diagnostics_flat_fields,
    execution_drift_overview_flat_fields,
    execution_gap_history_flat_fields,
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
    phase_gate_flat_fields,
)


def dict_or_empty(value: object) -> dict[str, Any]:
    return cast(dict[str, Any], value) if isinstance(value, dict) else {}


def quick_navigation(
    out_path: Path | None,
    phase_gate_report_path: str | None,
) -> dict[str, str]:
    if out_path is None:
        return {}
    items = (
        ("paper_vs_backtest_comparison_report", str(out_path)),
        ("phase_gate_review_report", phase_gate_report_path),
        ("current_state_index_report", str(out_path.parent / "current_state_index.md")),
        ("readiness_snapshot_report", str(out_path.parent / "readiness_snapshot.md")),
        ("paper_operations_runbook_report", str(out_path.parent / "paper_operations_runbook.md")),
    )
    return {key: value for key, value in items if isinstance(value, str) and value}


def related_reports(
    out_path: Path | None,
    row: dict[str, object],
) -> dict[str, str]:
    if out_path is None:
        return {}
    phase_gate = row.get("phase_gate")
    phase_gate_report_path = None
    if isinstance(phase_gate, dict):
        phase_gate_report_path = phase_gate_flat_fields(
            normalize_phase_gate_summary(dict_or_empty(phase_gate))
        ).get("phase_gate_review_report_path")
    items = (
        ("paper_vs_backtest_comparison_report", str(out_path)),
        ("phase_gate_review_report", phase_gate_report_path),
        ("current_state_index_report", str(out_path.parent / "current_state_index.md")),
        ("readiness_snapshot_report", str(out_path.parent / "readiness_snapshot.md")),
        ("operations_dashboard_report", str(out_path.parent / "operations_dashboard.md")),
        ("paper_operations_runbook_report", str(out_path.parent / "paper_operations_runbook.md")),
    )
    execution_summary = row.get("execution_summary")
    if isinstance(execution_summary, dict):
        items += (
            (
                "execution_snapshot_report",
                execution_snapshot_flat_fields(
                    normalize_execution_snapshot_summary(dict_or_empty(execution_summary))
                ).get("execution_report_path"),
            ),
        )
    execution_comparison = row.get("execution_comparison_summary")
    if isinstance(execution_comparison, dict):
        items += (
            (
                "execution_venue_comparison_report",
                execution_comparison_flat_fields(
                    normalize_execution_comparison_summary(dict_or_empty(execution_comparison))
                ).get("execution_comparison_report_path"),
            ),
        )
    execution_diagnostics = row.get("execution_diagnostics_summary")
    if isinstance(execution_diagnostics, dict):
        items += (
            (
                "execution_venue_diagnostics_report",
                execution_diagnostics_flat_fields(
                    normalize_execution_diagnostics_summary(dict_or_empty(execution_diagnostics))
                ).get("execution_diagnostics_report_path"),
            ),
        )
    execution_gap_history = row.get("execution_gap_history_summary")
    if isinstance(execution_gap_history, dict):
        items += (
            (
                "execution_gap_history_report",
                execution_gap_history_flat_fields(
                    normalize_execution_gap_history_summary(dict_or_empty(execution_gap_history))
                ).get("execution_gap_history_report_path"),
            ),
        )
    execution_state_comparison = row.get("execution_state_comparison_summary")
    if isinstance(execution_state_comparison, dict):
        items += (
            (
                "execution_state_comparison_report",
                execution_state_comparison_flat_fields(
                    normalize_execution_state_comparison_summary(
                        dict_or_empty(execution_state_comparison)
                    )
                ).get("execution_state_comparison_report_path"),
            ),
        )
    execution_snapshot_drift = row.get("execution_snapshot_drift_summary")
    if isinstance(execution_snapshot_drift, dict):
        items += (
            (
                "execution_snapshot_drift_report",
                execution_snapshot_drift_flat_fields(
                    normalize_execution_snapshot_drift_summary(
                        dict_or_empty(execution_snapshot_drift)
                    )
                ).get("execution_snapshot_drift_report_path"),
            ),
        )
    execution_drift_overview = row.get("execution_drift_overview_summary")
    if isinstance(execution_drift_overview, dict):
        items += (
            (
                "execution_drift_overview_report",
                execution_drift_overview_flat_fields(
                    normalize_execution_drift_overview_summary(
                        dict_or_empty(execution_drift_overview)
                    )
                ).get("execution_drift_overview_report_path"),
            ),
        )
    return {key: value for key, value in items if isinstance(value, str) and value}
