from __future__ import annotations

import pytest

from sis.backtest.engine.fill import resolve_market_like_fill_price


def test_resolve_market_like_fill_price_prefers_exec_prices() -> None:
    entry_price, entry_source = resolve_market_like_fill_price(
        {"exec_buy_price": 101.0, "best_ask": 102.0}, side="buy"
    )
    exit_price, exit_source = resolve_market_like_fill_price(
        {"exec_sell_price": 99.0, "best_bid": 98.0}, side="sell"
    )

    assert (entry_price, entry_source) == (101.0, "exec_buy_price")
    assert (exit_price, exit_source) == (99.0, "exec_sell_price")


def test_resolve_market_like_fill_price_falls_back_to_book_or_mid_spread() -> None:
    entry_price, entry_source = resolve_market_like_fill_price(
        {"mid_price": 100.0, "spread_bps": 20.0}, side="buy"
    )
    exit_price, exit_source = resolve_market_like_fill_price(
        {"mid_price": 100.0, "spread_bps": 20.0}, side="sell"
    )

    assert entry_price == pytest.approx(100.1)
    assert entry_source == "mid_plus_half_spread"
    assert exit_price == pytest.approx(99.9)
    assert exit_source == "mid_minus_half_spread"


def test_resolve_market_like_fill_price_does_not_use_ohlc() -> None:
    assert resolve_market_like_fill_price(
        {"open": 100, "high": 101, "low": 99, "close": 100}, side="buy"
    ) == (
        None,
        None,
    )
