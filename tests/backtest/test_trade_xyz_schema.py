from __future__ import annotations

from datetime import datetime, timezone

import polars as pl
import pytest

from sis.backtest.trade_xyz.schema import normalize_trade_xyz_market_data


def test_normalize_trade_xyz_market_data_maps_current_quote_columns() -> None:
    frame = pl.DataFrame(
        {
            "ts_client": ["2026-01-01T00:00:00Z"],
            "canonical_symbol": ["sp500"],
            "index_price": [100.0],
            "best_bid": [99.9],
            "best_ask": [100.1],
            "mid_price": [100.0],
            "taker_fee_bps": [9.0],
            "maker_fee_bps": [3.0],
            "is_tradable": [True],
            "block_reasons": [[]],
        }
    )

    normalized = normalize_trade_xyz_market_data(frame, symbol="SP500")

    assert normalized.select("event_ts").item() == datetime(2026, 1, 1, tzinfo=timezone.utc)
    assert normalized.select("symbol").item() == "SP500"
    assert normalized.select("external_price").item() == 100.0
    assert normalized.get_column("block_reasons").to_list() == [[]]


def test_normalize_trade_xyz_market_data_rejects_symbol_mismatch() -> None:
    frame = pl.DataFrame(
        {
            "event_ts": [datetime(2026, 1, 1, tzinfo=timezone.utc)],
            "symbol": ["XYZ100"],
            "mid_price": [100.0],
            "spread_bps": [1.0],
            "fee_mode": ["standard"],
            "is_tradable": [True],
            "block_reasons": [[]],
        }
    )

    with pytest.raises(ValueError, match="symbol mismatch"):
        normalize_trade_xyz_market_data(frame, symbol="SP500")


def test_normalize_trade_xyz_market_data_treats_list_null_as_empty_block_reasons() -> None:
    frame = pl.DataFrame(
        {
            "event_ts": [datetime(2026, 1, 1, tzinfo=timezone.utc)],
            "symbol": ["SP500"],
            "mid_price": [100.0],
            "spread_bps": [1.0],
            "fee_mode": ["standard"],
            "is_tradable": [True],
            "block_reasons": [[]],
        }
    ).with_columns(pl.col("block_reasons").cast(pl.List(pl.Null)))

    normalized = normalize_trade_xyz_market_data(frame, symbol="SP500")

    assert normalized.schema["block_reasons"] == pl.List(pl.Utf8)
    assert normalized.get_column("block_reasons").to_list() == [[]]
