from __future__ import annotations

from pathlib import Path

from sis.commands.report_writer_common import write_operation_chain_report
from sis.reports.execution_drift_overview import build_execution_drift_overview_report
from sis.reports.execution_gap_history import build_execution_gap_history_report
from sis.reports.execution_snapshot_drift_history import (
    build_execution_snapshot_drift_history_report,
)
from sis.reports.execution_state_comparison_history import (
    build_execution_state_comparison_history_report,
)


def _write_execution_gap_history(settings_data_dir: Path) -> tuple[Path, Path, str]:
    return write_operation_chain_report(
        settings_data_dir=settings_data_dir,
        report_filename="execution_gap_history.md",
        summary_filename="execution_gap_history_summary.json",
        build_report=build_execution_gap_history_report,
    )


def _write_execution_state_comparison_history(settings_data_dir: Path) -> tuple[Path, Path, str]:
    return write_operation_chain_report(
        settings_data_dir=settings_data_dir,
        report_filename="execution_state_comparison_history.md",
        summary_filename="execution_state_comparison_history_summary.json",
        build_report=build_execution_state_comparison_history_report,
    )


def _write_execution_snapshot_drift_history(settings_data_dir: Path) -> tuple[Path, Path, str]:
    return write_operation_chain_report(
        settings_data_dir=settings_data_dir,
        report_filename="execution_snapshot_drift_history.md",
        summary_filename="execution_snapshot_drift_history_summary.json",
        build_report=build_execution_snapshot_drift_history_report,
    )


def _write_execution_drift_overview(settings_data_dir: Path) -> tuple[Path, Path, str]:
    out = settings_data_dir / "reports/execution_drift_overview.md"
    summary_out = settings_data_dir / "ops/execution_drift_overview_summary.json"
    text = build_execution_drift_overview_report(
        execution_gap_history_summary_path=settings_data_dir
        / "ops/execution_gap_history_summary.json",
        execution_state_comparison_history_summary_path=(
            settings_data_dir / "ops/execution_state_comparison_history_summary.json"
        ),
        execution_snapshot_drift_history_summary_path=(
            settings_data_dir / "ops/execution_snapshot_drift_history_summary.json"
        ),
        out_path=out,
        summary_path=summary_out,
    )
    return out, summary_out, text
