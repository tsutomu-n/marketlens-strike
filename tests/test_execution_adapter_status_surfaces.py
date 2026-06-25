from __future__ import annotations

from pathlib import Path

from sis.reports.execution_adapter_status_surfaces import (
    build_execution_read_only_surfaces_summary,
)


def test_read_only_surfaces_summary_preserves_existing_counts_and_numeric_coercion() -> None:
    out_path = Path("data/reports/execution_read_only_surfaces.md")
    venue_surfaces = [
        {
            "venue": "gtrade",
            "balance_snapshot_exists": True,
            "positions_snapshot_exists": True,
            "fills_snapshot_exists": True,
            "order_status_snapshot_exists": True,
            "reconcile_matched": 1,
            "positions_notional_usd_total": "10.5",
            "positions_unrealized_pnl_usd_total": "1.5",
            "positions_collateral_used_usd_total": 3,
            "positions_max_withdrawable_usd_total": "4",
            "positions_cumulative_rollover_usd_total": "0.25",
            "positions_with_liquidation_price_count": "2",
            "positions_with_take_profit_count": 1.9,
            "positions_with_stop_loss_count": "bad",
            "positions_day_trade_count": True,
            "positions_server_time_ms": "100",
            "positions_average_leverage": "6.0",
            "positions_average_return_on_equity": "0.2",
            "positions_max_leverage": "30",
            "positions_total_quantity": "5",
            "positions_total_realized_pnl": "7",
            "positions_latest_open_timestamp_ms": "90",
            "positions_latest_updated_at": "2026-05-24T01:00:00+00:00",
            "positions_client_ts": "2026-05-24T01:00:00+00:00",
        },
        {
            "venue": "ostium",
            "collector_status": "not_connected",
            "balance_snapshot_exists": False,
            "positions_snapshot_exists": False,
            "fills_snapshot_exists": False,
            "order_status_snapshot_exists": False,
            "positions_notional_usd_total": "bad",
            "positions_average_leverage": "bad",
            "positions_average_return_on_equity": False,
            "positions_max_leverage": False,
            "positions_server_time_ms": 200,
            "positions_latest_open_timestamp_ms": 80,
            "positions_latest_updated_at": "2026-05-24T02:00:00+00:00",
            "positions_client_ts": "2026-05-24T00:00:00+00:00",
        },
    ]

    summary = build_execution_read_only_surfaces_summary(
        venue_surfaces=venue_surfaces,
        out_path=out_path,
    )
    venue_surfaces[0]["venue"] = "mutated"

    assert summary["venue_count"] == 2
    assert summary["venues"][0]["venue"] == "gtrade"
    assert summary["with_balance_snapshot_count"] == 1
    assert summary["with_positions_snapshot_count"] == 1
    assert summary["with_fills_snapshot_count"] == 1
    assert summary["with_order_status_snapshot_count"] == 1
    assert summary["unavailable_venue_count"] == 1
    assert summary["reconciled_venue_count"] == 1
    assert summary["with_positions_financial_totals_count"] == 2
    assert summary["positions_notional_usd_total"] == 10.5
    assert summary["positions_unrealized_pnl_usd_total"] == 1.5
    assert summary["positions_collateral_used_usd_total"] == 3.0
    assert summary["positions_max_withdrawable_usd_total"] == 4.0
    assert summary["positions_cumulative_rollover_usd_total"] == 0.25
    assert summary["with_positions_protection_metrics_count"] == 1
    assert summary["positions_with_liquidation_price_count"] == 2
    assert summary["positions_with_take_profit_count"] == 1
    assert summary["positions_with_stop_loss_count"] == 0
    assert summary["positions_day_trade_count"] == 0
    assert summary["with_positions_leverage_metrics_count"] == 2
    assert summary["positions_average_leverage"] == 3.0
    assert summary["with_positions_return_metrics_count"] == 2
    assert summary["positions_average_return_on_equity"] == 0.1
    assert summary["positions_max_leverage"] == 30.0
    assert summary["positions_total_quantity"] == 5.0
    assert summary["positions_total_realized_pnl"] == 7.0
    assert summary["latest_positions_server_time_ms"] == 200
    assert summary["latest_positions_open_timestamp_ms"] == 90
    assert summary["latest_positions_updated_at"] == "2026-05-24T02:00:00+00:00"
    assert summary["latest_positions_client_ts"] == "2026-05-24T01:00:00+00:00"
    assert summary["execution_read_only_surfaces_report_path"] == str(out_path)
    assert summary["quick_navigation"]["execution_adapter_report"] == str(out_path)
    assert summary["related_reports"]["execution_snapshot_report"] == (
        "data/reports/execution_snapshot.md"
    )
    assert "data/reports/execution_snapshot.md" in summary["recommended_read_order"]


def test_read_only_surfaces_summary_handles_missing_output_path() -> None:
    summary = build_execution_read_only_surfaces_summary(
        venue_surfaces=[],
        out_path=None,
    )

    assert summary["venue_count"] == 0
    assert summary["execution_read_only_surfaces_report_path"] is None
    assert summary["quick_navigation"] == {}
    assert summary["related_reports"] == {}
    assert summary["positions_average_leverage"] is None
    assert summary["positions_average_return_on_equity"] is None
    assert summary["latest_positions_server_time_ms"] is None
