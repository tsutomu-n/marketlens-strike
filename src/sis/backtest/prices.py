from __future__ import annotations

from collections.abc import Mapping


PriceRow = Mapping[str, object]


def execution_price(row: PriceRow, side: str = "long") -> float | None:
    keys = (
        ("exec_sell_price", "mark_price", "mid_price", "oracle_price", "index_price")
        if side == "short"
        else ("exec_buy_price", "mark_price", "mid_price", "oracle_price", "index_price")
    )
    for key in keys:
        value = row.get(key)
        if isinstance(value, int | float) and value > 0:
            return float(value)
    return None


def exit_price(row: PriceRow, side: str = "long") -> float | None:
    keys = (
        ("exec_buy_price", "mark_price", "mid_price", "oracle_price", "index_price")
        if side == "short"
        else ("exec_sell_price", "mark_price", "mid_price", "oracle_price", "index_price")
    )
    for key in keys:
        value = row.get(key)
        if isinstance(value, int | float) and value > 0:
            return float(value)
    return None


def net_return(entry_price: float, exit_price: float, side: str, cost_bps: float) -> float:
    gross = exit_price / entry_price - 1.0
    if side == "short":
        gross = entry_price / exit_price - 1.0
    return gross - cost_bps / 10_000


def gross_return_bps(entry_price: float, exit_price: float, side: str) -> float:
    gross = exit_price / entry_price - 1.0
    if side == "short":
        gross = entry_price / exit_price - 1.0
    return gross * 10_000
