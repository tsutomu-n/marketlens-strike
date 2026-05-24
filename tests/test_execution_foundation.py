from __future__ import annotations

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
        positions_root / "positions_2026-05-24.json",
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

    assert len(positions) == 1
    assert positions[0].canonical_symbol == "SPY"
    assert positions[0].quantity == 2.0
    assert estimate.estimated_cost_bps == 3.0
    assert estimate.price_reference == "bid_ask_or_price_after_impact"
