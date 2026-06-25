from __future__ import annotations

from pathlib import Path

from sis.reports.execution_adapter_status_navigation import (
    execution_adapter_recommended_read_order,
    quick_navigation,
    related_reports,
)


def _as_float(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            return float(text)
        except ValueError:
            return None
    return None


def _as_int(value: object) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            return int(text)
        except ValueError:
            return None
    return None


def _sum_float_field(venues: list[dict[str, object]], field: str) -> float:
    return sum(value for item in venues if (value := _as_float(item.get(field))) is not None)


def _sum_int_field(venues: list[dict[str, object]], field: str) -> int:
    return sum(value for item in venues if (value := _as_int(item.get(field))) is not None)


def build_execution_read_only_surfaces_summary(
    *,
    venue_surfaces: list[dict[str, object]],
    out_path: Path | None = None,
) -> dict[str, object]:
    venues = [dict(item) for item in venue_surfaces]
    venue_count = len(venues)
    with_balance_snapshot_count = sum(bool(item.get("balance_snapshot_exists")) for item in venues)
    with_positions_snapshot_count = sum(
        bool(item.get("positions_snapshot_exists")) for item in venues
    )
    with_fills_snapshot_count = sum(bool(item.get("fills_snapshot_exists")) for item in venues)
    with_order_status_snapshot_count = sum(
        bool(item.get("order_status_snapshot_exists")) for item in venues
    )
    unavailable_venue_count = sum(
        item.get("collector_status") in {"not_connected", "unavailable"} for item in venues
    )
    reconciled_venue_count = sum(item.get("reconcile_matched") is not None for item in venues)
    with_positions_financial_totals_count = sum(
        item.get("positions_notional_usd_total") is not None for item in venues
    )
    with_positions_rollover_metrics_count = sum(
        item.get("positions_cumulative_rollover_usd_total") is not None for item in venues
    )
    with_positions_protection_metrics_count = sum(
        item.get("positions_with_liquidation_price_count") is not None for item in venues
    )
    with_positions_leverage_metrics_count = sum(
        item.get("positions_average_leverage") is not None for item in venues
    )
    with_positions_return_metrics_count = sum(
        item.get("positions_average_return_on_equity") is not None for item in venues
    )
    with_positions_day_trade_metrics_count = sum(
        item.get("positions_day_trade_count") is not None for item in venues
    )
    with_positions_limit_metrics_count = sum(
        item.get("positions_max_leverage") is not None for item in venues
    )
    with_positions_quantity_metrics_count = sum(
        item.get("positions_total_quantity") is not None for item in venues
    )
    positions_notional_usd_total = _sum_float_field(venues, "positions_notional_usd_total")
    positions_unrealized_pnl_usd_total = _sum_float_field(
        venues, "positions_unrealized_pnl_usd_total"
    )
    positions_collateral_used_usd_total = _sum_float_field(
        venues, "positions_collateral_used_usd_total"
    )
    positions_max_withdrawable_usd_total = _sum_float_field(
        venues, "positions_max_withdrawable_usd_total"
    )
    positions_cumulative_rollover_usd_total = _sum_float_field(
        venues, "positions_cumulative_rollover_usd_total"
    )
    positions_with_liquidation_price_count = _sum_int_field(
        venues, "positions_with_liquidation_price_count"
    )
    positions_with_take_profit_count = _sum_int_field(venues, "positions_with_take_profit_count")
    positions_with_stop_loss_count = _sum_int_field(venues, "positions_with_stop_loss_count")
    positions_day_trade_count = _sum_int_field(venues, "positions_day_trade_count")
    latest_positions_server_time_ms = max(
        (
            value
            for item in venues
            if (value := _as_int(item.get("positions_server_time_ms"))) is not None
        ),
        default=None,
    )
    positions_average_leverage = (
        _sum_float_field(venues, "positions_average_leverage")
        / with_positions_leverage_metrics_count
        if with_positions_leverage_metrics_count
        else None
    )
    positions_average_return_on_equity = (
        _sum_float_field(venues, "positions_average_return_on_equity")
        / with_positions_return_metrics_count
        if with_positions_return_metrics_count
        else None
    )
    positions_max_leverage = max(
        (
            value
            for item in venues
            if (value := _as_float(item.get("positions_max_leverage"))) is not None
        ),
        default=None,
    )
    positions_total_quantity = _sum_float_field(venues, "positions_total_quantity")
    positions_total_realized_pnl = _sum_float_field(venues, "positions_total_realized_pnl")
    latest_positions_open_timestamp_ms = max(
        (
            value
            for item in venues
            if (value := _as_int(item.get("positions_latest_open_timestamp_ms"))) is not None
        ),
        default=None,
    )
    latest_positions_updated_at = max(
        (
            str(item.get("positions_latest_updated_at"))
            for item in venues
            if item.get("positions_latest_updated_at") is not None
        ),
        default=None,
    )
    latest_positions_client_ts = max(
        (
            str(item.get("positions_client_ts"))
            for item in venues
            if item.get("positions_client_ts") is not None
        ),
        default=None,
    )
    return {
        "venue_count": venue_count,
        "venues": venues,
        "with_balance_snapshot_count": with_balance_snapshot_count,
        "with_positions_snapshot_count": with_positions_snapshot_count,
        "with_fills_snapshot_count": with_fills_snapshot_count,
        "with_order_status_snapshot_count": with_order_status_snapshot_count,
        "unavailable_venue_count": unavailable_venue_count,
        "reconciled_venue_count": reconciled_venue_count,
        "with_positions_financial_totals_count": with_positions_financial_totals_count,
        "with_positions_rollover_metrics_count": with_positions_rollover_metrics_count,
        "with_positions_protection_metrics_count": with_positions_protection_metrics_count,
        "with_positions_leverage_metrics_count": with_positions_leverage_metrics_count,
        "with_positions_return_metrics_count": with_positions_return_metrics_count,
        "with_positions_day_trade_metrics_count": with_positions_day_trade_metrics_count,
        "with_positions_limit_metrics_count": with_positions_limit_metrics_count,
        "with_positions_quantity_metrics_count": with_positions_quantity_metrics_count,
        "positions_notional_usd_total": positions_notional_usd_total,
        "positions_unrealized_pnl_usd_total": positions_unrealized_pnl_usd_total,
        "positions_collateral_used_usd_total": positions_collateral_used_usd_total,
        "positions_max_withdrawable_usd_total": positions_max_withdrawable_usd_total,
        "positions_cumulative_rollover_usd_total": positions_cumulative_rollover_usd_total,
        "positions_with_liquidation_price_count": positions_with_liquidation_price_count,
        "positions_with_take_profit_count": positions_with_take_profit_count,
        "positions_with_stop_loss_count": positions_with_stop_loss_count,
        "positions_day_trade_count": positions_day_trade_count,
        "positions_average_leverage": positions_average_leverage,
        "positions_average_return_on_equity": positions_average_return_on_equity,
        "positions_max_leverage": positions_max_leverage,
        "positions_total_quantity": positions_total_quantity,
        "positions_total_realized_pnl": positions_total_realized_pnl,
        "latest_positions_server_time_ms": latest_positions_server_time_ms,
        "latest_positions_open_timestamp_ms": latest_positions_open_timestamp_ms,
        "latest_positions_updated_at": latest_positions_updated_at,
        "latest_positions_client_ts": latest_positions_client_ts,
        "execution_read_only_surfaces_report_path": str(out_path) if out_path is not None else None,
        "recommended_read_order": execution_adapter_recommended_read_order(),
        "quick_navigation": quick_navigation(out_path),
        "related_reports": related_reports(out_path),
    }
