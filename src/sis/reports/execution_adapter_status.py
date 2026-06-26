from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Mapping, cast

from sis.execution.base import AdapterActionResult, AdapterFillSnapshot, AdapterOrderStatus
from sis.reports.execution_adapter_status_navigation import (
    execution_adapter_recommended_read_order as _recommended_read_order,
    report_context as _report_context,
)
from sis.reports.execution_adapter_status_surfaces import (
    build_execution_read_only_surfaces_summary,
)
from sis.state.reconciliation import ReconciliationResult
from sis.storage.jsonl_store import write_json


def _write_report(
    *,
    title: str,
    summary: Mapping[str, object],
    detail_lines: list[str],
    out_path: Path | None = None,
    summary_path: Path | None = None,
) -> str:
    quick_navigation = summary.get("quick_navigation")
    related_reports = summary.get("related_reports")
    lines = [f"# {title}", ""]
    if isinstance(quick_navigation, dict) and quick_navigation:
        lines.extend(["## Quick Navigation", ""])
        lines.extend(f"- {key}: {value}" for key, value in quick_navigation.items())
        lines.append("")
    if isinstance(related_reports, dict) and related_reports:
        lines.extend(["## Related Reports", ""])
        lines.extend(f"- {key}: {value}" for key, value in related_reports.items())
        lines.append("")
    lines.extend(["## Overview", "", *detail_lines, "", "## Recommended Read Order", ""])
    lines.extend(f"- {item}" for item in _recommended_read_order())
    lines.append("")
    text = "\n".join(lines)
    if out_path is not None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text, encoding="utf-8")
    if summary_path is not None:
        write_json(summary_path, summary)
    return text


def build_balance_status_report(
    *,
    venue: str,
    balance: dict[str, object],
    out_path: Path | None = None,
    summary_path: Path | None = None,
) -> str:
    summary = {
        "venue": venue,
        "balance": balance,
        "mode": balance.get("mode"),
        "currency": balance.get("currency"),
        "equity": balance.get("equity"),
        "available_cash": balance.get("available_cash"),
        "margin_used": balance.get("margin_used"),
        "notional_usd": balance.get("notional_usd"),
        "unrealized_pnl": balance.get("unrealized_pnl"),
        "cumulative_rollover_usd": balance.get("cumulative_rollover_usd"),
        "balance_snapshot_exists": balance.get("balance_snapshot_exists"),
        "balance_status_report_path": str(out_path) if out_path is not None else None,
        **_report_context(out_path),
    }
    return _write_report(
        title="Execution Balance Status",
        summary=summary,
        detail_lines=[
            f"- venue: {summary['venue']}",
            f"- mode: {summary['mode']}",
            f"- currency: {summary['currency']}",
            f"- equity: {summary['equity']}",
            f"- available_cash: {summary['available_cash']}",
            f"- margin_used: {summary['margin_used']}",
            f"- notional_usd: {summary['notional_usd']}",
            f"- unrealized_pnl: {summary['unrealized_pnl']}",
            f"- cumulative_rollover_usd: {summary['cumulative_rollover_usd']}",
            f"- balance_snapshot_exists: {summary['balance_snapshot_exists']}",
        ],
        out_path=out_path,
        summary_path=summary_path,
    )


def build_fill_status_report(
    *,
    venue: str,
    fills: list[AdapterFillSnapshot],
    limit: int,
    out_path: Path | None = None,
    summary_path: Path | None = None,
) -> str:
    rows = [asdict(fill) for fill in fills]
    summary = {
        "venue": venue,
        "fills_count": len(rows),
        "limit": limit,
        "fills": rows,
        "latest_fill_id": rows[0]["fill_id"] if rows else None,
        "latest_fill_order_id": rows[0]["order_id"] if rows else None,
        "latest_fill_symbol": rows[0]["canonical_symbol"] if rows else None,
        "latest_fill_side": rows[0]["side"] if rows else None,
        "latest_fill_quantity": rows[0]["quantity"] if rows else None,
        "latest_fill_price": rows[0]["price"] if rows else None,
        "latest_fill_status": rows[0]["status"] if rows else None,
        "latest_fill_ts_fill": rows[0]["ts_fill"] if rows else None,
        "fill_status_report_path": str(out_path) if out_path is not None else None,
        **_report_context(out_path),
    }
    detail_lines = [
        f"- venue: {summary['venue']}",
        f"- fills_count: {summary['fills_count']}",
        f"- limit: {summary['limit']}",
        f"- latest_fill_id: {summary['latest_fill_id']}",
        f"- latest_fill_order_id: {summary['latest_fill_order_id']}",
        f"- latest_fill_symbol: {summary['latest_fill_symbol']}",
        f"- latest_fill_side: {summary['latest_fill_side']}",
        f"- latest_fill_quantity: {summary['latest_fill_quantity']}",
        f"- latest_fill_price: {summary['latest_fill_price']}",
        f"- latest_fill_status: {summary['latest_fill_status']}",
        f"- latest_fill_ts_fill: {summary['latest_fill_ts_fill']}",
    ]
    for index, row in enumerate(rows, start=1):
        detail_lines.extend(
            [
                f"- fill_{index}_id: {row['fill_id']}",
                f"- fill_{index}_order_id: {row['order_id']}",
                f"- fill_{index}_symbol: {row['canonical_symbol']}",
                f"- fill_{index}_side: {row['side']}",
                f"- fill_{index}_quantity: {row['quantity']}",
                f"- fill_{index}_price: {row['price']}",
                f"- fill_{index}_status: {row['status']}",
                f"- fill_{index}_ts_fill: {row['ts_fill']}",
            ]
        )
    return _write_report(
        title="Execution Fill Status",
        summary=summary,
        detail_lines=detail_lines,
        out_path=out_path,
        summary_path=summary_path,
    )


def build_order_status_report(
    *,
    status: AdapterOrderStatus,
    out_path: Path | None = None,
    summary_path: Path | None = None,
) -> str:
    summary = {
        "venue": status.venue,
        "order_id": status.order_id,
        "symbol": status.canonical_symbol,
        "side": status.side,
        "quantity": status.quantity,
        "status": status.status,
        "notes": status.notes,
        "order_status_report_path": str(out_path) if out_path is not None else None,
        **_report_context(out_path),
    }
    return _write_report(
        title="Execution Order Status",
        summary=summary,
        detail_lines=[
            f"- venue: {summary['venue']}",
            f"- order_id: {summary['order_id']}",
            f"- status: {summary['status']}",
            f"- symbol: {summary['symbol']}",
            f"- side: {summary['side']}",
            f"- quantity: {summary['quantity']}",
            f"- notes: {','.join(status.notes)}",
        ],
        out_path=out_path,
        summary_path=summary_path,
    )


def build_action_status_report(
    *,
    title: str,
    report_key: str,
    result: AdapterActionResult,
    out_path: Path | None = None,
    summary_path: Path | None = None,
) -> str:
    summary = {
        "venue": result.venue,
        "action": result.action,
        "target": result.target,
        "success": result.success,
        "status": result.status,
        "notes": result.notes,
        report_key: str(out_path) if out_path is not None else None,
        **_report_context(out_path),
    }
    return _write_report(
        title=title,
        summary=summary,
        detail_lines=[
            f"- venue: {summary['venue']}",
            f"- action: {summary['action']}",
            f"- target: {summary['target']}",
            f"- success: {summary['success']}",
            f"- status: {summary['status']}",
            f"- notes: {','.join(result.notes)}",
        ],
        out_path=out_path,
        summary_path=summary_path,
    )


def build_reconcile_positions_report(
    *,
    venue: str,
    result: ReconciliationResult,
    run_id: str,
    state_store_path: str,
    out_path: Path | None = None,
    summary_path: Path | None = None,
) -> str:
    summary = {
        "venue": venue,
        "run_id": run_id,
        "matched": result.matched,
        "missing_in_adapter": result.missing_in_adapter,
        "missing_in_internal": result.missing_in_internal,
        "missing_in_adapter_count": len(result.missing_in_adapter),
        "missing_in_internal_count": len(result.missing_in_internal),
        "state_store_path": state_store_path,
        "reconcile_positions_report_path": str(out_path) if out_path is not None else None,
        **_report_context(out_path),
    }
    detail_lines = [
        f"- venue: {summary['venue']}",
        f"- run_id: {summary['run_id']}",
        f"- matched: {summary['matched']}",
        f"- missing_in_adapter_count: {summary['missing_in_adapter_count']}",
        f"- missing_in_internal_count: {summary['missing_in_internal_count']}",
        f"- state_store_path: {summary['state_store_path']}",
    ]
    for index, item in enumerate(result.missing_in_adapter, start=1):
        detail_lines.append(f"- missing_in_adapter_{index}: {item}")
    for index, item in enumerate(result.missing_in_internal, start=1):
        detail_lines.append(f"- missing_in_internal_{index}: {item}")
    return _write_report(
        title="Execution Position Reconciliation",
        summary=summary,
        detail_lines=detail_lines,
        out_path=out_path,
        summary_path=summary_path,
    )


def build_execution_read_only_surfaces_report(
    *,
    venue_surfaces: list[dict[str, object]],
    out_path: Path | None = None,
    summary_path: Path | None = None,
) -> str:
    summary = build_execution_read_only_surfaces_summary(
        venue_surfaces=venue_surfaces,
        out_path=out_path,
    )
    venues = cast(list[dict[str, object]], summary["venues"])
    venue_count = summary["venue_count"]
    with_balance_snapshot_count = summary["with_balance_snapshot_count"]
    with_positions_snapshot_count = summary["with_positions_snapshot_count"]
    with_fills_snapshot_count = summary["with_fills_snapshot_count"]
    with_order_status_snapshot_count = summary["with_order_status_snapshot_count"]
    unavailable_venue_count = summary["unavailable_venue_count"]
    reconciled_venue_count = summary["reconciled_venue_count"]
    with_positions_financial_totals_count = summary["with_positions_financial_totals_count"]
    with_positions_rollover_metrics_count = summary["with_positions_rollover_metrics_count"]
    with_positions_protection_metrics_count = summary["with_positions_protection_metrics_count"]
    with_positions_leverage_metrics_count = summary["with_positions_leverage_metrics_count"]
    with_positions_return_metrics_count = summary["with_positions_return_metrics_count"]
    with_positions_day_trade_metrics_count = summary["with_positions_day_trade_metrics_count"]
    with_positions_limit_metrics_count = summary["with_positions_limit_metrics_count"]
    with_positions_quantity_metrics_count = summary["with_positions_quantity_metrics_count"]
    positions_notional_usd_total = summary["positions_notional_usd_total"]
    positions_unrealized_pnl_usd_total = summary["positions_unrealized_pnl_usd_total"]
    positions_collateral_used_usd_total = summary["positions_collateral_used_usd_total"]
    positions_max_withdrawable_usd_total = summary["positions_max_withdrawable_usd_total"]
    positions_cumulative_rollover_usd_total = summary["positions_cumulative_rollover_usd_total"]
    positions_with_liquidation_price_count = summary["positions_with_liquidation_price_count"]
    positions_with_take_profit_count = summary["positions_with_take_profit_count"]
    positions_with_stop_loss_count = summary["positions_with_stop_loss_count"]
    positions_day_trade_count = summary["positions_day_trade_count"]
    positions_average_leverage = summary["positions_average_leverage"]
    positions_average_return_on_equity = summary["positions_average_return_on_equity"]
    positions_max_leverage = summary["positions_max_leverage"]
    positions_total_quantity = summary["positions_total_quantity"]
    positions_total_realized_pnl = summary["positions_total_realized_pnl"]
    latest_positions_server_time_ms = summary["latest_positions_server_time_ms"]
    latest_positions_open_timestamp_ms = summary["latest_positions_open_timestamp_ms"]
    latest_positions_updated_at = summary["latest_positions_updated_at"]
    latest_positions_client_ts = summary["latest_positions_client_ts"]
    detail_lines = [
        f"- venue_count: {venue_count}",
        f"- with_balance_snapshot_count: {with_balance_snapshot_count}",
        f"- with_positions_snapshot_count: {with_positions_snapshot_count}",
        f"- with_fills_snapshot_count: {with_fills_snapshot_count}",
        f"- with_order_status_snapshot_count: {with_order_status_snapshot_count}",
        f"- unavailable_venue_count: {unavailable_venue_count}",
        f"- reconciled_venue_count: {reconciled_venue_count}",
        f"- with_positions_financial_totals_count: {with_positions_financial_totals_count}",
        f"- with_positions_rollover_metrics_count: {with_positions_rollover_metrics_count}",
        f"- with_positions_protection_metrics_count: {with_positions_protection_metrics_count}",
        f"- with_positions_leverage_metrics_count: {with_positions_leverage_metrics_count}",
        f"- with_positions_return_metrics_count: {with_positions_return_metrics_count}",
        f"- with_positions_day_trade_metrics_count: {with_positions_day_trade_metrics_count}",
        f"- with_positions_limit_metrics_count: {with_positions_limit_metrics_count}",
        f"- with_positions_quantity_metrics_count: {with_positions_quantity_metrics_count}",
        f"- positions_notional_usd_total: {positions_notional_usd_total}",
        f"- positions_unrealized_pnl_usd_total: {positions_unrealized_pnl_usd_total}",
        f"- positions_collateral_used_usd_total: {positions_collateral_used_usd_total}",
        f"- positions_max_withdrawable_usd_total: {positions_max_withdrawable_usd_total}",
        f"- positions_cumulative_rollover_usd_total: {positions_cumulative_rollover_usd_total}",
        f"- positions_with_liquidation_price_count: {positions_with_liquidation_price_count}",
        f"- positions_with_take_profit_count: {positions_with_take_profit_count}",
        f"- positions_with_stop_loss_count: {positions_with_stop_loss_count}",
        f"- positions_day_trade_count: {positions_day_trade_count}",
        f"- positions_average_leverage: {positions_average_leverage}",
        f"- positions_average_return_on_equity: {positions_average_return_on_equity}",
        f"- positions_max_leverage: {positions_max_leverage}",
        f"- positions_total_quantity: {positions_total_quantity}",
        f"- positions_total_realized_pnl: {positions_total_realized_pnl}",
        f"- latest_positions_server_time_ms: {latest_positions_server_time_ms}",
        f"- latest_positions_open_timestamp_ms: {latest_positions_open_timestamp_ms}",
        f"- latest_positions_updated_at: {latest_positions_updated_at}",
        f"- latest_positions_client_ts: {latest_positions_client_ts}",
    ]
    for item in venues:
        venue = item.get("venue")
        detail_lines.extend(
            [
                f"- venue_{venue}_balance_snapshot_exists: {item.get('balance_snapshot_exists')}",
                f"- venue_{venue}_collector_status: {item.get('collector_status')}",
                f"- venue_{venue}_collector_reason: {item.get('collector_reason')}",
                f"- venue_{venue}_collector_root_source: {item.get('collector_root_source')}",
                f"- venue_{venue}_read_only_endpoint_scope: {item.get('read_only_endpoint_scope')}",
                f"- venue_{venue}_next_action: {item.get('next_action')}",
                f"- venue_{venue}_positions_snapshot_exists: {item.get('positions_snapshot_exists')}",
                f"- venue_{venue}_fills_snapshot_exists: {item.get('fills_snapshot_exists')}",
                f"- venue_{venue}_order_status_snapshot_exists: {item.get('order_status_snapshot_exists')}",
                f"- venue_{venue}_equity: {item.get('equity')}",
                f"- venue_{venue}_available_cash: {item.get('available_cash')}",
                f"- venue_{venue}_margin_used: {item.get('margin_used')}",
                f"- venue_{venue}_notional_usd: {item.get('notional_usd')}",
                f"- venue_{venue}_unrealized_pnl: {item.get('unrealized_pnl')}",
                f"- venue_{venue}_cumulative_rollover_usd: {item.get('cumulative_rollover_usd')}",
                f"- venue_{venue}_fills_count: {item.get('fills_count')}",
                f"- venue_{venue}_latest_fill_id: {item.get('latest_fill_id')}",
                f"- venue_{venue}_order_status_count: {item.get('order_status_count')}",
                f"- venue_{venue}_latest_order_id: {item.get('latest_order_id')}",
                f"- venue_{venue}_latest_order_status: {item.get('latest_order_status')}",
                f"- venue_{venue}_positions_count: {item.get('positions_count')}",
                f"- venue_{venue}_positions_server_time_ms: {item.get('positions_server_time_ms')}",
                f"- venue_{venue}_positions_notional_usd_total: {item.get('positions_notional_usd_total')}",
                f"- venue_{venue}_positions_unrealized_pnl_usd_total: {item.get('positions_unrealized_pnl_usd_total')}",
                f"- venue_{venue}_positions_collateral_used_usd_total: {item.get('positions_collateral_used_usd_total')}",
                f"- venue_{venue}_positions_max_withdrawable_usd_total: {item.get('positions_max_withdrawable_usd_total')}",
                f"- venue_{venue}_positions_cumulative_rollover_usd_total: {item.get('positions_cumulative_rollover_usd_total')}",
                f"- venue_{venue}_positions_with_liquidation_price_count: {item.get('positions_with_liquidation_price_count')}",
                f"- venue_{venue}_positions_with_take_profit_count: {item.get('positions_with_take_profit_count')}",
                f"- venue_{venue}_positions_with_stop_loss_count: {item.get('positions_with_stop_loss_count')}",
                f"- venue_{venue}_positions_day_trade_count: {item.get('positions_day_trade_count')}",
                f"- venue_{venue}_positions_average_leverage: {item.get('positions_average_leverage')}",
                f"- venue_{venue}_positions_average_return_on_equity: {item.get('positions_average_return_on_equity')}",
                f"- venue_{venue}_positions_max_leverage: {item.get('positions_max_leverage')}",
                f"- venue_{venue}_positions_latest_open_timestamp_ms: {item.get('positions_latest_open_timestamp_ms')}",
                f"- venue_{venue}_positions_total_quantity: {item.get('positions_total_quantity')}",
                f"- venue_{venue}_positions_total_realized_pnl: {item.get('positions_total_realized_pnl')}",
                f"- venue_{venue}_positions_latest_updated_at: {item.get('positions_latest_updated_at')}",
                f"- venue_{venue}_positions_client_ts: {item.get('positions_client_ts')}",
                f"- venue_{venue}_reconcile_matched: {item.get('reconcile_matched')}",
                (
                    f"- venue_{venue}_reconcile_missing_in_adapter_count: "
                    f"{item.get('reconcile_missing_in_adapter_count')}"
                ),
                (
                    f"- venue_{venue}_reconcile_missing_in_internal_count: "
                    f"{item.get('reconcile_missing_in_internal_count')}"
                ),
            ]
        )
    return _write_report(
        title="Execution Read Only Surfaces",
        summary=summary,
        detail_lines=detail_lines,
        out_path=out_path,
        summary_path=summary_path,
    )
