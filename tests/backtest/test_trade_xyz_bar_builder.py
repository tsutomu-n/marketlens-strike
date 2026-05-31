from __future__ import annotations

import polars as pl

from sis.backtest.trade_xyz.bar_builder import build_quote_bars


def test_build_quote_bars_separates_signal_fields_from_fill_snapshot() -> None:
    frame = pl.DataFrame(
        {
            "ts_client": [
                "2026-01-01T00:00:00+00:00",
                "2026-01-01T00:30:00+00:00",
                "2026-01-01T01:00:00+00:00",
            ],
            "canonical_symbol": ["SP500", "SP500", "SP500"],
            "mid_price": [100.0, 102.0, 101.0],
            "best_bid": [99.9, 101.9, 100.9],
            "best_ask": [100.1, 102.1, 101.1],
            "spread_bps": [2.0, 20.0, 3.0],
            "taker_fee_bps": [9.0, 9.0, 9.0],
            "maker_fee_bps": [3.0, 3.0, 3.0],
            "fee_mode": ["standard", "standard", "standard"],
            "market_status": ["open", "halted", "open"],
            "is_tradable": [True, False, True],
            "block_reasons": [[], ["HALT"], []],
            "session_type": ["regular", "regular", "regular"],
        }
    )

    bars = build_quote_bars(frame, symbol="SP500", timeframe="1h")
    first = bars.row(0, named=True)

    assert first["open"] == 100.0
    assert first["high"] == 102.0
    assert first["low"] == 100.0
    assert first["close"] == 102.0
    assert first["signal_is_tradable"] is False
    assert first["signal_market_status"] == "halted"
    assert first["signal_block_reasons"] == ["HALT"]
    assert first["fill_is_tradable"] is True
    assert first["fill_market_status"] == "open"
    assert first["fill_block_reasons"] == []
    assert first["bar_block_reason_union"] == ["HALT"]
    assert first["exec_buy_price"] is None
    assert first["exec_sell_price"] is None
    assert first["fill_best_ask"] == 100.1
    assert first["fill_best_bid"] == 99.9
