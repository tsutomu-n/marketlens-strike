from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

import typer

from sis.execution.bitget_demo_adapter import BitgetDemoAdapter
from sis.reports.execution_adapter_status import build_execution_read_only_surfaces_report
from sis.reports.execution_snapshot import build_execution_snapshot_report
from sis.reports.execution_venue_comparison import build_execution_venue_comparison_report
from sis.reports.execution_venue_diagnostics import build_execution_venue_diagnostics_report


def _adapter_for_venue(settings_data_dir: Path, venue: str):
    del settings_data_dir
    normalized = venue.strip().lower()
    if normalized == "bitget_demo":
        return BitgetDemoAdapter.from_env()
    raise typer.BadParameter(
        f"Unsupported venue: {venue}. Legacy gTrade/Ostium adapters were zipped and removed; "
        "Trade[XYZ] live execution is exposed through the micro-live safety path, not this "
        "legacy read-only adapter surface."
    )


def _trade_xyz_read_only_surface(settings_data_dir: Path) -> dict[str, object]:
    registry_path = settings_data_dir / "registry/trade_xyz_instrument_registry.json"
    return {
        "venue": "trade_xyz",
        "registry_exists": registry_path.exists(),
        "balance_snapshot_exists": False,
        "positions_snapshot_exists": False,
        "fills_snapshot_exists": False,
        "order_status_snapshot_exists": False,
        "positions_count": None,
        "fills_count": None,
        "order_status_count": None,
        "collector_status": "not_connected",
        "collector_reason": "read_only_execution_state_collector_not_implemented",
        "collector_root_source": "execution_read_only_surfaces_summary.venues[].collector_status",
        "read_only_endpoint_scope": "info_endpoint_only",
        "next_action": "connect_trade_xyz_read_only_execution_state_collector",
    }


def _bitget_demo_read_only_surface() -> dict[str, object]:
    healthcheck = BitgetDemoAdapter.from_env().healthcheck()
    return {
        "venue": "bitget_demo",
        "registry_exists": False,
        "balance_snapshot_exists": False,
        "positions_snapshot_exists": False,
        "fills_snapshot_exists": False,
        "order_status_snapshot_exists": False,
        "positions_count": 0,
        "fills_count": 0,
        "order_status_count": 0,
        "collector_status": "not_connected",
        "collector_reason": "bitget_demo_read_only_network_probe_not_executed",
        "collector_root_source": "bitget_demo_adapter.healthcheck",
        "read_only_endpoint_scope": "local_healthcheck_only",
        "credential_status": healthcheck["credential_status"],
        "missing_env": healthcheck["missing_env"],
        "external_write_enabled": False,
        "paptrading_header": healthcheck["paptrading_header"],
        "next_action": "set_bitget_demo_credentials_then_run_bitget_demo_smoke",
    }


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
        venue_snapshots=[
            _trade_xyz_read_only_surface(settings_data_dir),
            _bitget_demo_read_only_surface(),
        ],
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
        venue_surfaces=[
            _trade_xyz_read_only_surface(settings_data_dir),
            _bitget_demo_read_only_surface(),
        ],
        out_path=out,
        summary_path=summary_out,
    )
    return out, summary_out, text
