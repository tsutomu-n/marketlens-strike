from __future__ import annotations

from pathlib import Path

from sis.reports.phase_gate_review import build_phase_gate_review


def _write_phase_gate_review(settings_data_dir: Path) -> tuple[Path, Path, str]:
    out = settings_data_dir / "reports/phase_gate_review.md"
    summary_out = settings_data_dir / "ops/phase_gate_review_summary.json"
    text = build_phase_gate_review(
        settings_data_dir,
        schema_root=Path(__file__).resolve().parents[3] / "schemas",
        execution_snapshot_summary_path=settings_data_dir / "ops/execution_snapshot_summary.json",
        execution_venue_comparison_summary_path=settings_data_dir
        / "ops/execution_venue_comparison_summary.json",
        execution_venue_diagnostics_summary_path=settings_data_dir
        / "ops/execution_venue_diagnostics_summary.json",
        execution_gap_history_summary_path=settings_data_dir
        / "ops/execution_gap_history_summary.json",
        execution_state_comparison_history_summary_path=(
            settings_data_dir / "ops/execution_state_comparison_history_summary.json"
        ),
        execution_snapshot_drift_history_summary_path=(
            settings_data_dir / "ops/execution_snapshot_drift_history_summary.json"
        ),
        execution_drift_overview_summary_path=settings_data_dir
        / "ops/execution_drift_overview_summary.json",
        remediation_planner_summary_path=settings_data_dir / "ops/remediation_planner_summary.json",
        remediation_evaluator_summary_path=settings_data_dir
        / "ops/remediation_evaluator_summary.json",
        out_path=out,
        summary_path=summary_out,
    )
    return out, summary_out, text
