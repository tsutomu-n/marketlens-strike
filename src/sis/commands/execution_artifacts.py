from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Callable

import polars as pl
import typer

from sis.execution.archive.gtrade_adapter import GTradeExecutionAdapter
from sis.execution.archive.ostium_adapter import OstiumExecutionAdapter
from sis.paper.portfolio import PaperPosition
from sis.reports.execution_adapter_status import build_execution_read_only_surfaces_report
from sis.reports.execution_snapshot import build_execution_snapshot_report
from sis.reports.execution_venue_comparison import build_execution_venue_comparison_report
from sis.reports.execution_venue_diagnostics import build_execution_venue_diagnostics_report
from sis.state.reconciliation import reconcile_positions
from sis.storage.jsonl_store import read_json
from sis.venues.archive.ostium.positions import latest_positions_sidecar


def _adapter_for_venue(settings_data_dir: Path, venue: str):
    normalized = venue.strip().lower()
    if normalized == "gtrade":
        return GTradeExecutionAdapter(
            registry_path=settings_data_dir / "registry/gtrade_instrument_registry.json",
            balance_snapshot_path=settings_data_dir / "execution/gtrade_balance.json",
            positions_snapshot_path=settings_data_dir / "paper/positions.parquet",
            fills_snapshot_path=settings_data_dir / "execution/gtrade_fills.json",
            order_status_path=settings_data_dir / "execution/gtrade_order_status.json",
        )
    if normalized == "ostium":
        return OstiumExecutionAdapter(
            registry_path=settings_data_dir / "registry/ostium_instrument_registry.json",
            positions_root=settings_data_dir / "raw/sidecar/ostium",
            balance_snapshot_path=settings_data_dir / "execution/ostium_balance.json",
            fills_snapshot_path=settings_data_dir / "execution/ostium_fills.json",
            order_status_path=settings_data_dir / "execution/ostium_order_status.json",
        )
    raise typer.BadParameter(f"Unsupported venue: {venue}")


def _execution_snapshot_for_venue(
    settings_data_dir: Path,
    venue: str,
    *,
    fills_limit: int,
    order_limit: int,
) -> dict:
    adapter = _adapter_for_venue(settings_data_dir, venue)
    balance = adapter.read_balance()
    positions = adapter.read_positions()
    fills = adapter.read_fills(limit=fills_limit)
    order_statuses = adapter.read_order_statuses(limit=order_limit)
    health = adapter.healthcheck()
    return {
        "venue": venue.strip().lower(),
        "registry_exists": health.get("registry_exists"),
        "balance_snapshot_exists": health.get("balance_snapshot_exists"),
        "positions_snapshot_exists": health.get("positions_snapshot_exists"),
        "fills_snapshot_exists": health.get("fills_snapshot_exists"),
        "order_status_snapshot_exists": health.get("order_status_snapshot_exists"),
        "positions_count": len(positions),
        "fills_count": len(fills),
        "order_status_count": len(order_statuses),
        "balance": balance,
        "latest_fill": fills[0].__dict__ if fills else None,
        "latest_order_status": order_statuses[0].__dict__ if order_statuses else None,
    }


def _write_execution_snapshot(
    settings_data_dir: Path,
    *,
    venue: str | None = None,
    fills_limit: int = 5,
    order_limit: int = 5,
) -> tuple[Path, Path, str]:
    venues = [venue] if venue is not None else ["gtrade", "ostium"]
    venue_snapshots = [
        _execution_snapshot_for_venue(
            settings_data_dir,
            venue_name,
            fills_limit=fills_limit,
            order_limit=order_limit,
        )
        for venue_name in venues
    ]
    out = settings_data_dir / "reports/execution_snapshot.md"
    summary_out = settings_data_dir / "ops/execution_snapshot_summary.json"
    text = build_execution_snapshot_report(
        venue_snapshots=venue_snapshots,
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
        execution_venue_comparison_summary_path=settings_data_dir / "ops/execution_venue_comparison_summary.json",
        out_path=out,
        summary_path=summary_out,
    )
    return out, summary_out, text

def _has_target_free_execution_observation_sources(settings_data_dir: Path) -> bool:
    source_paths = [
        settings_data_dir / "execution/gtrade_balance.json",
        settings_data_dir / "execution/ostium_balance.json",
        settings_data_dir / "execution/gtrade_fills.json",
        settings_data_dir / "execution/ostium_fills.json",
        settings_data_dir / "execution/gtrade_order_status.json",
        settings_data_dir / "execution/ostium_order_status.json",
        settings_data_dir / "paper/positions.parquet",
    ]
    if any(path.exists() for path in source_paths):
        return True
    return latest_positions_sidecar(settings_data_dir / "raw/sidecar/ostium") is not None


def _refresh_execution_lineage_artifacts(
    settings_data_dir: Path,
    *,
    only_if_sources_exist: bool = False,
    write_execution_gap_history_fn: Callable[[Path], tuple[Path, Path, str]],
    write_execution_state_comparison_history_fn: Callable[[Path], tuple[Path, Path, str]],
    write_execution_snapshot_drift_history_fn: Callable[[Path], tuple[Path, Path, str]],
    write_execution_drift_overview_fn: Callable[[Path], tuple[Path, Path, str]],
) -> dict[str, tuple[Path, Path, str]]:
    if only_if_sources_exist and not _has_target_free_execution_observation_sources(settings_data_dir):
        return {}
    execution_snapshot_out, execution_snapshot_summary_out, execution_snapshot_text = _write_execution_snapshot(
        settings_data_dir
    )
    execution_comparison_out, execution_comparison_summary_out, execution_comparison_text = _write_execution_venue_comparison(
        settings_data_dir
    )
    execution_diagnostics_out, execution_diagnostics_summary_out, execution_diagnostics_text = _write_execution_venue_diagnostics(
        settings_data_dir
    )
    gap_history_out, gap_history_summary_out, gap_history_text = write_execution_gap_history_fn(settings_data_dir)
    state_comparison_out, state_comparison_summary_out, state_comparison_text = write_execution_state_comparison_history_fn(settings_data_dir)
    snapshot_drift_out, snapshot_drift_summary_out, snapshot_drift_text = write_execution_snapshot_drift_history_fn(settings_data_dir)
    drift_overview_out, drift_overview_summary_out, drift_overview_text = write_execution_drift_overview_fn(settings_data_dir)
    return {
        "execution_snapshot": (execution_snapshot_out, execution_snapshot_summary_out, execution_snapshot_text),
        "execution_comparison": (execution_comparison_out, execution_comparison_summary_out, execution_comparison_text),
        "execution_diagnostics": (execution_diagnostics_out, execution_diagnostics_summary_out, execution_diagnostics_text),
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
        "execution_drift_overview": (drift_overview_out, drift_overview_summary_out, drift_overview_text),
    }


def _execution_read_only_surface_for_venue(
    settings_data_dir: Path,
    venue: str,
    *,
    state_path: Path | None = None,
    fills_limit: int = 20,
    order_limit: int = 20,
    state_store_fn: Callable[[Path, Path | None], Any],
) -> dict[str, object]:
    def _float_or_none(value: object) -> float | None:
        if isinstance(value, int | float):
            return float(value)
        if isinstance(value, str):
            try:
                return float(value)
            except ValueError:
                return None
        return None

    def _int_or_none(value: object) -> int | None:
        if isinstance(value, int):
            return value
        if isinstance(value, str):
            try:
                return int(value)
            except ValueError:
                return None
        return None

    def _timestamp_ms_or_none(value: object) -> int | None:
        if hasattr(value, "timestamp"):
            return int(value.timestamp() * 1000)
        if isinstance(value, str):
            try:
                return int(datetime.fromisoformat(value).timestamp() * 1000)
            except ValueError:
                return None
        return None

    adapter = _adapter_for_venue(settings_data_dir, venue)
    balance = adapter.read_balance()
    positions = adapter.read_positions()
    fills = adapter.read_fills(limit=fills_limit)
    order_statuses = adapter.read_order_statuses(limit=order_limit)
    health = adapter.healthcheck()
    store = state_store_fn(settings_data_dir, state_path)
    payload = store.get_json("paper_positions")
    internal_positions = (
        [
            PaperPosition.model_validate(item)
            for item in payload
            if isinstance(item, dict) and str(item.get("venue", "")).lower() == venue
        ]
        if isinstance(payload, list)
        else []
    )
    reconciliation = reconcile_positions(internal_positions, positions)
    latest_fill = fills[0].__dict__ if fills else {}
    latest_order_status = order_statuses[0].__dict__ if order_statuses else {}
    positions_server_time_ms = None
    positions_notional_usd_total = None
    positions_unrealized_pnl_usd_total = None
    positions_collateral_used_usd_total = None
    positions_max_withdrawable_usd_total = None
    positions_cumulative_rollover_usd_total = None
    positions_average_leverage = None
    positions_average_return_on_equity = None
    positions_max_leverage = None
    positions_with_liquidation_price_count = None
    positions_with_take_profit_count = None
    positions_with_stop_loss_count = None
    positions_day_trade_count = None
    positions_latest_open_timestamp_ms = None
    positions_total_quantity = None
    positions_total_realized_pnl = None
    positions_latest_updated_at = None
    positions_client_ts = None
    if venue == "gtrade":
        positions_path = settings_data_dir / "paper/positions.parquet"
        if positions_path.exists():
            frame = pl.read_parquet(positions_path).filter(
                pl.col("venue").cast(pl.Utf8).str.to_lowercase() == venue
            )
            if frame.height:
                positions_total_quantity = float(frame["quantity"].sum()) if "quantity" in frame.columns else None
                positions_total_realized_pnl = (
                    float(frame["realized_pnl"].sum()) if "realized_pnl" in frame.columns else None
                )
                if {"quantity", "avg_entry_price"} <= set(frame.columns):
                    positions_notional_usd_total = float(
                        (frame["quantity"] * frame["avg_entry_price"]).sum()
                    )
                if "opened_at" in frame.columns:
                    latest_opened = frame["opened_at"].max()
                    if latest_opened is not None:
                        positions_latest_open_timestamp_ms = _timestamp_ms_or_none(latest_opened)
                if "updated_at" in frame.columns:
                    latest_updated = frame["updated_at"].max()
                    if latest_updated is not None:
                        positions_latest_updated_at = (
                            latest_updated.isoformat()
                            if hasattr(latest_updated, "isoformat")
                            else str(latest_updated)
                        )
    if venue == "ostium":
        positions_path = latest_positions_sidecar(settings_data_dir / "raw/sidecar/ostium")
        if positions_path is not None:
            payload = read_json(positions_path)
            if isinstance(payload, dict):
                positions_rows = payload.get("positions", [])
                if isinstance(positions_rows, list):
                    notional_values = [
                        value
                        for item in positions_rows
                        if isinstance(item, dict)
                        for value in [_float_or_none(item.get("notional_usd"))]
                        if value is not None
                    ]
                    unrealized_values = [
                        value
                        for item in positions_rows
                        if isinstance(item, dict)
                        for value in [_float_or_none(item.get("unrealized_pnl_usd"))]
                        if value is not None
                    ]
                    collateral_values = [
                        value
                        for item in positions_rows
                        if isinstance(item, dict)
                        for value in [_float_or_none(item.get("collateral_used_usd"))]
                        if value is not None
                    ]
                    withdrawable_values = [
                        value
                        for item in positions_rows
                        if isinstance(item, dict)
                        for value in [_float_or_none(item.get("max_withdrawable_usd"))]
                        if value is not None
                    ]
                    rollover_values = [
                        value
                        for item in positions_rows
                        if isinstance(item, dict)
                        for value in [_float_or_none(item.get("cumulative_rollover_usd"))]
                        if value is not None
                    ]
                    leverage_values = [
                        value
                        for item in positions_rows
                        if isinstance(item, dict)
                        for value in [_float_or_none(item.get("leverage"))]
                        if value is not None
                    ]
                    return_on_equity_values = [
                        value
                        for item in positions_rows
                        if isinstance(item, dict)
                        for value in [_float_or_none(item.get("return_on_equity"))]
                        if value is not None
                    ]
                    max_leverage_values = [
                        value
                        for item in positions_rows
                        if isinstance(item, dict)
                        for value in [_float_or_none(item.get("max_leverage"))]
                        if value is not None
                    ]
                    open_timestamps = [
                        value
                        for item in positions_rows
                        if isinstance(item, dict)
                        for value in [_int_or_none(item.get("open_timestamp_ms"))]
                        if value is not None
                    ]
                    positions_with_liquidation_price_count = sum(
                        1
                        for item in positions_rows
                        if isinstance(item, dict) and item.get("liquidation_px") is not None
                    )
                    positions_with_take_profit_count = sum(
                        1
                        for item in positions_rows
                        if isinstance(item, dict) and item.get("take_profit_px") is not None
                    )
                    positions_with_stop_loss_count = sum(
                        1
                        for item in positions_rows
                        if isinstance(item, dict) and item.get("stop_loss_px") is not None
                    )
                    positions_day_trade_count = sum(
                        1
                        for item in positions_rows
                        if isinstance(item, dict) and bool(item.get("is_day_trade"))
                    )
                    positions_notional_usd_total = (
                        sum(notional_values) if notional_values else None
                    )
                    positions_unrealized_pnl_usd_total = (
                        sum(unrealized_values) if unrealized_values else None
                    )
                    positions_collateral_used_usd_total = (
                        sum(collateral_values) if collateral_values else None
                    )
                    positions_max_withdrawable_usd_total = (
                        sum(withdrawable_values) if withdrawable_values else None
                    )
                    positions_cumulative_rollover_usd_total = (
                        sum(rollover_values) if rollover_values else None
                    )
                    positions_average_leverage = (
                        sum(leverage_values) / len(leverage_values)
                        if leverage_values
                        else None
                    )
                    positions_average_return_on_equity = (
                        sum(return_on_equity_values) / len(return_on_equity_values)
                        if return_on_equity_values
                        else None
                    )
                    positions_max_leverage = (
                        max(max_leverage_values) if max_leverage_values else None
                    )
                    positions_latest_open_timestamp_ms = (
                        max(open_timestamps) if open_timestamps else None
                    )
                positions_server_time_ms = _int_or_none(payload.get("server_time_ms"))
                positions_client_ts = (
                    str(payload.get("ts_client")) if payload.get("ts_client") is not None else None
                )
    return {
        "venue": venue,
        "balance_snapshot_exists": health.get("balance_snapshot_exists"),
        "positions_snapshot_exists": health.get("positions_snapshot_exists"),
        "fills_snapshot_exists": health.get("fills_snapshot_exists"),
        "order_status_snapshot_exists": health.get("order_status_snapshot_exists"),
        "currency": balance.get("currency"),
        "equity": balance.get("equity"),
        "available_cash": balance.get("available_cash"),
        "margin_used": balance.get("margin_used"),
        "notional_usd": balance.get("notional_usd"),
        "unrealized_pnl": balance.get("unrealized_pnl"),
        "cumulative_rollover_usd": balance.get("cumulative_rollover_usd"),
        "fills_count": len(fills),
        "latest_fill_id": latest_fill.get("fill_id"),
        "latest_fill_status": latest_fill.get("status"),
        "order_status_count": len(order_statuses),
        "latest_order_id": latest_order_status.get("order_id"),
        "latest_order_status": latest_order_status.get("status"),
        "positions_count": len(positions),
        "positions_server_time_ms": positions_server_time_ms,
        "positions_notional_usd_total": positions_notional_usd_total,
        "positions_unrealized_pnl_usd_total": positions_unrealized_pnl_usd_total,
        "positions_collateral_used_usd_total": positions_collateral_used_usd_total,
        "positions_max_withdrawable_usd_total": positions_max_withdrawable_usd_total,
        "positions_cumulative_rollover_usd_total": positions_cumulative_rollover_usd_total,
        "positions_average_leverage": positions_average_leverage,
        "positions_average_return_on_equity": positions_average_return_on_equity,
        "positions_max_leverage": positions_max_leverage,
        "positions_with_liquidation_price_count": positions_with_liquidation_price_count,
        "positions_with_take_profit_count": positions_with_take_profit_count,
        "positions_with_stop_loss_count": positions_with_stop_loss_count,
        "positions_day_trade_count": positions_day_trade_count,
        "positions_latest_open_timestamp_ms": positions_latest_open_timestamp_ms,
        "positions_total_quantity": positions_total_quantity,
        "positions_total_realized_pnl": positions_total_realized_pnl,
        "positions_latest_updated_at": positions_latest_updated_at,
        "positions_client_ts": positions_client_ts,
        "reconcile_matched": reconciliation.matched,
        "reconcile_missing_in_adapter_count": len(reconciliation.missing_in_adapter),
        "reconcile_missing_in_internal_count": len(reconciliation.missing_in_internal),
    }


def _write_execution_read_only_surfaces(
    settings_data_dir: Path,
    *,
    state_path: Path | None = None,
    state_store_fn: Callable[[Path, Path | None], Any],
) -> tuple[Path, Path, str]:
    venues = ["gtrade", "ostium"]
    venue_surfaces = [
        _execution_read_only_surface_for_venue(
            settings_data_dir,
            venue,
            state_path=state_path,
            state_store_fn=state_store_fn,
        )
        for venue in venues
    ]
    out = settings_data_dir / "reports/execution_read_only_surfaces.md"
    summary_out = settings_data_dir / "ops/execution_read_only_surfaces_summary.json"
    text = build_execution_read_only_surfaces_report(
        venue_surfaces=venue_surfaces,
        out_path=out,
        summary_path=summary_out,
    )
    return out, summary_out, text
