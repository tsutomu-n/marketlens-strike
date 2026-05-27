from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

import typer

from sis.reports.execution_adapter_status import build_execution_read_only_surfaces_report
from sis.reports.execution_snapshot import build_execution_snapshot_report
from sis.reports.execution_venue_comparison import build_execution_venue_comparison_report
from sis.reports.execution_venue_diagnostics import build_execution_venue_diagnostics_report


def _adapter_for_venue(settings_data_dir: Path, venue: str):
    raise typer.BadParameter(
        f"Unsupported venue: {venue}. Legacy gTrade/Ostium adapters were zipped and removed; "
        "Trade[XYZ] live execution is exposed through the micro-live safety path, not this "
        "legacy read-only adapter surface."
    )


def _write_execution_snapshot(
    settings_data_dir: Path,
    *,
    venue: str | None = None,
    fills_limit: int = 5,
    order_limit: int = 5,
) -> tuple[Path, Path, str]:
    out = settings_data_dir / "reports/execution_snapshot.md"
    summary_out = settings_data_dir / "ops/execution_snapshot_summary.json"
    text = build_execution_snapshot_report(
        venue_snapshots=[],
        out_path=out,
        summary_path=summary_out,
    )
    return out, summary_out, text


def _write_execution_venue_comparison(settings_data_dir: Path) -> tuple[Path, Path, str]:
    out = settings_data_dir / "reports/execution_venue_comparison.md"
    summary_out = settings_data_dir / "ops/execution_venue_comparison_summary.json"
    text = build_execution_venue_comparison_report(
        execution_snapshot_summary_path=settings_data_dir / "ops/execution_snapshot_summary.json",
        out_path=out,
        summary_path=summary_out,
    )
    return out, summary_out, text


def _write_execution_venue_diagnostics(settings_data_dir: Path) -> tuple[Path, Path, str]:
    out = settings_data_dir / "reports/execution_venue_diagnostics.md"
    summary_out = settings_data_dir / "ops/execution_venue_diagnostics_summary.json"
    text = build_execution_venue_diagnostics_report(
        execution_venue_comparison_summary_path=settings_data_dir
        / "ops/execution_venue_comparison_summary.json",
        out_path=out,
        summary_path=summary_out,
    )
    return out, summary_out, text


def _refresh_execution_lineage_artifacts(
    settings_data_dir: Path,
    *,
    only_if_sources_exist: bool = False,
    write_execution_gap_history_fn: Callable[[Path], tuple[Path, Path, str]],
    write_execution_state_comparison_history_fn: Callable[[Path], tuple[Path, Path, str]],
    write_execution_snapshot_drift_history_fn: Callable[[Path], tuple[Path, Path, str]],
    write_execution_drift_overview_fn: Callable[[Path], tuple[Path, Path, str]],
) -> dict[str, tuple[Path, Path, str]]:
    if only_if_sources_exist:
        return {}
    execution_snapshot_out, execution_snapshot_summary_out, execution_snapshot_text = (
        _write_execution_snapshot(settings_data_dir)
    )
    execution_comparison_out, execution_comparison_summary_out, execution_comparison_text = (
        _write_execution_venue_comparison(settings_data_dir)
    )
    execution_diagnostics_out, execution_diagnostics_summary_out, execution_diagnostics_text = (
        _write_execution_venue_diagnostics(settings_data_dir)
    )
    gap_history_out, gap_history_summary_out, gap_history_text = write_execution_gap_history_fn(
        settings_data_dir
    )
    state_comparison_out, state_comparison_summary_out, state_comparison_text = (
        write_execution_state_comparison_history_fn(settings_data_dir)
    )
    snapshot_drift_out, snapshot_drift_summary_out, snapshot_drift_text = (
        write_execution_snapshot_drift_history_fn(settings_data_dir)
    )
    drift_overview_out, drift_overview_summary_out, drift_overview_text = (
        write_execution_drift_overview_fn(settings_data_dir)
    )
    return {
        "execution_snapshot": (
            execution_snapshot_out,
            execution_snapshot_summary_out,
            execution_snapshot_text,
        ),
        "execution_comparison": (
            execution_comparison_out,
            execution_comparison_summary_out,
            execution_comparison_text,
        ),
        "execution_diagnostics": (
            execution_diagnostics_out,
            execution_diagnostics_summary_out,
            execution_diagnostics_text,
        ),
        "execution_gap_history": (gap_history_out, gap_history_summary_out, gap_history_text),
        "execution_state_comparison_history": (
            state_comparison_out,
            state_comparison_summary_out,
            state_comparison_text,
        ),
        "execution_snapshot_drift_history": (
            snapshot_drift_out,
            snapshot_drift_summary_out,
            snapshot_drift_text,
        ),
        "execution_drift_overview": (
            drift_overview_out,
            drift_overview_summary_out,
            drift_overview_text,
        ),
    }


def _write_execution_read_only_surfaces(
    settings_data_dir: Path,
    *,
    state_path: Path | None = None,
    state_store_fn: Callable[[Path, Path | None], Any],
) -> tuple[Path, Path, str]:
    out = settings_data_dir / "reports/execution_read_only_surfaces.md"
    summary_out = settings_data_dir / "ops/execution_read_only_surfaces_summary.json"
    text = build_execution_read_only_surfaces_report(
        venue_surfaces=[],
        out_path=out,
        summary_path=summary_out,
    )
    return out, summary_out, text
