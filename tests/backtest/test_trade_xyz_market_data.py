from __future__ import annotations

from datetime import datetime, timezone

import polars as pl
import pytest

from sis.backtest.trade_xyz.market_data import (
    infer_period_from_event_ts,
    prepare_quote_rows_for_backtest,
)


def _quotes() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "ts_client": ["2026-01-01T00:00:00+00:00", "2026-01-01T00:01:00+00:00"],
            "source_ts_ms": [1767225600000, 1767225660000],
            "recv_ts_ms": [1767225601000, 1767225661000],
            "canonical_symbol": ["SP500", "SP500"],
            "mid_price": [100.0, 101.0],
            "mark_price": [100.2, 101.2],
            "best_bid": [99.9, 100.9],
            "best_ask": [100.1, 101.1],
            "bid_depth_10bps_usd": [1000.0, 900.0],
            "ask_depth_10bps_usd": [800.0, 1200.0],
            "fee_mode": ["standard", "standard"],
            "is_tradable": [True, True],
            "block_reasons": [[], []],
        }
    )


def test_prepare_quote_rows_filters_symbol_and_creates_close_from_source() -> None:
    frame = prepare_quote_rows_for_backtest(_quotes(), symbol="SP500", close_source="mid_price")

    assert frame.get_column("symbol").to_list() == ["SP500", "SP500"]
    assert frame.get_column("close").to_list() == [100.0, 101.0]
    assert frame.get_column("min_side_depth_10bps_usd").to_list() == [800.0, 900.0]
    assert frame.get_column("event_time_source").to_list() == ["ts_client", "ts_client"]
    assert frame.get_column("close_source").to_list() == ["mid_price", "mid_price"]


def test_prepare_quote_rows_accepts_symbol_column_without_aliasing_symbols() -> None:
    source = _quotes().rename({"canonical_symbol": "symbol"})

    assert prepare_quote_rows_for_backtest(source, symbol="SP500").height == 2
    with pytest.raises(ValueError, match="no rows for symbol"):
        prepare_quote_rows_for_backtest(source, symbol="SPY")


def test_prepare_quote_rows_rejects_missing_or_all_null_close_source() -> None:
    with pytest.raises(ValueError, match="missing close_source"):
        prepare_quote_rows_for_backtest(_quotes(), symbol="SP500", close_source="oracle_price")

    with pytest.raises(ValueError, match="all null"):
        prepare_quote_rows_for_backtest(
            _quotes().with_columns(pl.lit(None, dtype=pl.Float64).alias("oracle_price")),
            symbol="SP500",
            close_source="oracle_price",
        )


def test_prepare_quote_rows_can_use_source_timestamp_ms_and_infer_period() -> None:
    frame = prepare_quote_rows_for_backtest(
        _quotes(), symbol="SP500", event_time_source="source_ts_ms"
    )

    assert frame.get_column("event_ts").to_list()[0] == datetime(2026, 1, 1, tzinfo=timezone.utc)
    assert infer_period_from_event_ts(frame) == (
        datetime(2026, 1, 1, tzinfo=timezone.utc),
        datetime(2026, 1, 1, 0, 1, tzinfo=timezone.utc),
    )
