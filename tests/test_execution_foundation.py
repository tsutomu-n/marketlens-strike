from __future__ import annotations

import polars as pl

from sis.execution.base import OrderIntent
from sis.execution.gtrade_adapter import GTradeExecutionAdapter
from sis.execution.ostium_adapter import OstiumExecutionAdapter
from sis.storage.jsonl_store import write_json


def test_gtrade_execution_adapter_estimates_from_registry(tmp_path) -> None:
    registry_path = tmp_path / "gtrade_registry.json"
    write_json(
        registry_path,
        [
            {
                "canonical_symbol": "QQQ",
                "venue_symbol": "QQQ/USD",
                "opening_fee_bps": 5,
            }
        ],
    )
    adapter = GTradeExecutionAdapter(registry_path=registry_path)
    estimate = adapter.estimate_order(OrderIntent("gtrade", "QQQ", "long", 1.0, "4h"))

    assert estimate.venue == "gtrade"
    assert estimate.estimated_cost_bps == 5.0
    assert estimate.price_reference == "mark"


def test_gtrade_execution_adapter_reads_balance_snapshot_file(tmp_path) -> None:
    registry_path = tmp_path / "gtrade_registry.json"
    balance_snapshot_path = tmp_path / "gtrade_balance.json"
    write_json(registry_path, [])
    write_json(balance_snapshot_path, {"currency": "USD", "equity": 1234.5, "available_cash": 900.0})
    adapter = GTradeExecutionAdapter(
        registry_path=registry_path,
        balance_snapshot_path=balance_snapshot_path,
    )

    balance = adapter.read_balance()

    assert balance["venue"] == "gtrade"
    assert balance["equity"] == 1234.5
    assert balance["available_cash"] == 900.0
    assert balance["balance_snapshot_exists"] is True


def test_gtrade_execution_adapter_reads_fill_snapshot_file(tmp_path) -> None:
    registry_path = tmp_path / "gtrade_registry.json"
    fills_snapshot_path = tmp_path / "gtrade_fills.json"
    write_json(registry_path, [])
    write_json(
        fills_snapshot_path,
        [
            {
                "fill_id": "fill-1",
                "order_id": "ord-1",
                "canonical_symbol": "QQQ",
                "side": "long",
                "quantity": 1,
                "price": 100.5,
                "status": "filled",
                "ts_fill": "2026-05-24T00:00:00+00:00",
            }
        ],
    )
    adapter = GTradeExecutionAdapter(
        registry_path=registry_path,
        fills_snapshot_path=fills_snapshot_path,
    )

    fills = adapter.read_fills()

    assert len(fills) == 1
    assert fills[0].fill_id == "fill-1"
    assert fills[0].canonical_symbol == "QQQ"
    assert fills[0].price == 100.5


def test_gtrade_execution_adapter_reads_positions_snapshot_file(tmp_path) -> None:
    registry_path = tmp_path / "gtrade_registry.json"
    positions_snapshot_path = tmp_path / "positions.parquet"
    write_json(registry_path, [])
    pl.DataFrame(
        [
            {
                "venue": "gtrade",
                "canonical_symbol": "QQQ",
                "side": "long",
                "quantity": 2.0,
                "avg_entry_price": 101.5,
                "opened_at": "2026-05-24T00:00:00+00:00",
                "updated_at": "2026-05-24T01:00:00+00:00",
                "realized_pnl": 0.0,
            },
            {
                "venue": "ostium",
                "canonical_symbol": "SPY",
                "side": "long",
                "quantity": 1.0,
                "avg_entry_price": 500.0,
                "opened_at": "2026-05-24T00:00:00+00:00",
                "updated_at": "2026-05-24T01:00:00+00:00",
                "realized_pnl": 0.0,
            },
        ]
    ).write_parquet(positions_snapshot_path)
    adapter = GTradeExecutionAdapter(
        registry_path=registry_path,
        positions_snapshot_path=positions_snapshot_path,
    )

    positions = adapter.read_positions()
    health = adapter.healthcheck()

    assert len(positions) == 1
    assert positions[0].canonical_symbol == "QQQ"
    assert positions[0].quantity == 2.0
    assert positions[0].entry_price == 101.5
    assert health["positions_snapshot_exists"] is True


def test_gtrade_execution_adapter_order_status_and_cancel_close_are_read_only(tmp_path) -> None:
    registry_path = tmp_path / "gtrade_registry.json"
    order_status_path = tmp_path / "gtrade_order_status.json"
    write_json(registry_path, [])
    write_json(
        order_status_path,
        [{"order_id": "ord-1", "canonical_symbol": "QQQ", "side": "long", "quantity": 1, "status": "working"}],
    )
    adapter = GTradeExecutionAdapter(registry_path=registry_path, order_status_path=order_status_path)

    status = adapter.read_order_status("ord-1")
    cancel = adapter.cancel_order("ord-1")
    close = adapter.close_position("QQQ", "long")

    assert status.status == "working"
    assert status.canonical_symbol == "QQQ"
    assert cancel.success is False
    assert cancel.status == "blocked_read_only"
    assert close.success is False
    assert close.status == "blocked_read_only"


def test_ostium_execution_adapter_reads_positions_and_estimates(tmp_path) -> None:
    registry_path = tmp_path / "ostium_registry.json"
    positions_root = tmp_path / "raw/sidecar/ostium"
    write_json(
        registry_path,
        [
            {
                "canonical_symbol": "SPY",
                "venue_symbol": "US500-USD",
                "opening_fee_bps": 3,
            }
        ],
    )
    write_json(
        positions_root / "positions_all_2026-05-24.json",
        {
            "positions": [
                {
                    "venue_symbol": "US500-USD",
                    "side": "long",
                    "size": "2",
                    "entry_px": "100",
                    "liquidation_px": "80",
                }
            ]
        },
    )
    adapter = OstiumExecutionAdapter(registry_path=registry_path, positions_root=positions_root)

    positions = adapter.read_positions()
    estimate = adapter.estimate_order(OrderIntent("ostium", "SPY", "long", 1.0, "4h"))
    health = adapter.healthcheck()

    assert len(positions) == 1
    assert positions[0].canonical_symbol == "SPY"
    assert positions[0].quantity == 2.0
    assert estimate.estimated_cost_bps == 3.0
    assert estimate.price_reference == "bid_ask_or_price_after_impact"
    assert health["positions_snapshot_exists"] is True


def test_ostium_execution_adapter_reads_balance_snapshot_file(tmp_path) -> None:
    registry_path = tmp_path / "ostium_registry.json"
    positions_root = tmp_path / "raw/sidecar/ostium"
    balance_snapshot_path = tmp_path / "ostium_balance.json"
    write_json(registry_path, [])
    positions_root.mkdir(parents=True, exist_ok=True)
    write_json(balance_snapshot_path, {"currency": "USD", "equity": 2222.0, "margin_used": 150.0})
    adapter = OstiumExecutionAdapter(
        registry_path=registry_path,
        positions_root=positions_root,
        balance_snapshot_path=balance_snapshot_path,
    )

    balance = adapter.read_balance()

    assert balance["venue"] == "ostium"
    assert balance["equity"] == 2222.0
    assert balance["margin_used"] == 150.0
    assert balance["balance_snapshot_exists"] is True


def test_ostium_execution_adapter_infers_balance_from_positions_sidecar(tmp_path) -> None:
    registry_path = tmp_path / "ostium_registry.json"
    positions_root = tmp_path / "raw/sidecar/ostium"
    write_json(registry_path, [])
    write_json(
        positions_root / "positions_all_2026-05-24.json",
        {
            "positions": [],
            "margin_summary": {
                "accountValue": "2184177.7575539993",
                "totalCollateralUsed": "2158493.9945829986",
                "totalNtlPos": "24214944.037214246",
                "totalWithdrawable": "1752150.3245409152",
                "totalRawPnlUsd": "25683.762970999986",
                "totalCumRollover": "-1639.0377230000001",
            },
        },
    )
    adapter = OstiumExecutionAdapter(
        registry_path=registry_path,
        positions_root=positions_root,
    )

    balance = adapter.read_balance()

    assert balance["venue"] == "ostium"
    assert balance["equity"] == 2184177.7575539993
    assert balance["available_cash"] == 1752150.3245409152
    assert balance["margin_used"] == 2158493.9945829986
    assert balance["notional_usd"] == 24214944.037214246
    assert balance["unrealized_pnl"] == 25683.762970999986
    assert balance["cumulative_rollover_usd"] == -1639.0377230000001
    assert balance["balance_snapshot_exists"] is False


def test_ostium_execution_adapter_reads_fill_snapshot_file(tmp_path) -> None:
    registry_path = tmp_path / "ostium_registry.json"
    positions_root = tmp_path / "raw/sidecar/ostium"
    fills_snapshot_path = tmp_path / "ostium_fills.json"
    write_json(registry_path, [])
    positions_root.mkdir(parents=True, exist_ok=True)
    write_json(
        fills_snapshot_path,
        {
            "fills": [
                {
                    "fill_id": "fill-2",
                    "order_id": "ord-2",
                    "canonical_symbol": "SPY",
                    "side": "short",
                    "quantity": 2,
                    "price": 501.0,
                    "status": "filled",
                    "ts_fill": "2026-05-24T01:00:00+00:00",
                }
            ]
        },
    )
    adapter = OstiumExecutionAdapter(
        registry_path=registry_path,
        positions_root=positions_root,
        fills_snapshot_path=fills_snapshot_path,
    )

    fills = adapter.read_fills(limit=10)

    assert len(fills) == 1
    assert fills[0].fill_id == "fill-2"
    assert fills[0].canonical_symbol == "SPY"
    assert fills[0].side == "short"


def test_ostium_execution_adapter_order_status_and_cancel_close_are_read_only(tmp_path) -> None:
    registry_path = tmp_path / "ostium_registry.json"
    positions_root = tmp_path / "raw/sidecar/ostium"
    order_status_path = tmp_path / "ostium_order_status.json"
    write_json(registry_path, [])
    positions_root.mkdir(parents=True, exist_ok=True)
    write_json(
        order_status_path,
        [{"order_id": "ord-2", "canonical_symbol": "SPY", "side": "short", "quantity": 2, "status": "filled"}],
    )
    adapter = OstiumExecutionAdapter(
        registry_path=registry_path,
        positions_root=positions_root,
        order_status_path=order_status_path,
    )

    status = adapter.read_order_status("ord-2")
    cancel = adapter.cancel_order("ord-2")
    close = adapter.close_position("SPY", "short")

    assert status.status == "filled"
    assert status.side == "short"
    assert cancel.status == "blocked_read_only"
    assert close.status == "blocked_read_only"
