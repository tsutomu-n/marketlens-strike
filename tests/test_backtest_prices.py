from __future__ import annotations

import pytest

from sis.backtest.prices import execution_price, exit_price, gross_return_bps, net_return


def test_execution_price_prefers_side_specific_trade_price() -> None:
    row = {
        "exec_buy_price": 101.0,
        "exec_sell_price": 99.0,
        "mark_price": 100.0,
        "mid_price": 100.5,
        "oracle_price": 100.25,
        "index_price": 100.75,
    }

    assert execution_price(row, "long") == 101.0
    assert execution_price(row, "short") == 99.0


def test_execution_price_falls_back_to_mark_mid_oracle_index() -> None:
    assert execution_price({"mark_price": 100.0}, "long") == 100.0
    assert execution_price({"mid_price": 101.0}, "short") == 101.0
    assert execution_price({"oracle_price": 102.0}, "long") == 102.0
    assert execution_price({"index_price": 103.0}, "short") == 103.0
    assert execution_price({"exec_buy_price": 0.0, "mark_price": None}, "long") is None


def test_exit_price_uses_opposite_side_trade_price() -> None:
    row = {
        "exec_buy_price": 101.0,
        "exec_sell_price": 99.0,
        "mark_price": 100.0,
        "mid_price": 100.5,
    }

    assert exit_price(row, "long") == 99.0
    assert exit_price(row, "short") == 101.0


def test_return_helpers_handle_long_short_and_costs() -> None:
    assert net_return(100.0, 110.0, "long", 5.0) == pytest.approx(0.0995)
    assert net_return(100.0, 90.0, "short", 5.0) == pytest.approx(100.0 / 90.0 - 1.0 - 0.0005)
    assert gross_return_bps(100.0, 110.0, "long") == pytest.approx(1000.0)
    assert gross_return_bps(100.0, 90.0, "short") == pytest.approx((100.0 / 90.0 - 1.0) * 10_000)
