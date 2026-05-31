from __future__ import annotations

import polars as pl

from sis.backtest.engine.fill import Fill
from sis.backtest.engine.order import Order


def orders_to_frame(orders: list[Order]) -> pl.DataFrame:
    schema = {
        "order_id": pl.Utf8,
        "client_order_id": pl.Utf8,
        "created_ts": pl.Datetime(time_zone="UTC"),
        "symbol": pl.Utf8,
        "side": pl.Utf8,
        "position_effect": pl.Utf8,
        "order_type": pl.Utf8,
        "requested_notional_usd": pl.Float64,
        "requested_qty": pl.Float64,
        "limit_price": pl.Null,
        "reduce_only": pl.Boolean,
        "strategy_id": pl.Utf8,
        "signal_id": pl.Utf8,
    }
    if not orders:
        return pl.DataFrame(schema=schema)
    return pl.from_dicts([order.model_dump(mode="python") for order in orders], schema=schema)


def fills_to_frame(fills: list[Fill]) -> pl.DataFrame:
    schema = {
        "fill_id": pl.Utf8,
        "order_id": pl.Utf8,
        "event_ts": pl.Datetime(time_zone="UTC"),
        "symbol": pl.Utf8,
        "side": pl.Utf8,
        "position_effect": pl.Utf8,
        "qty": pl.Float64,
        "fill_price": pl.Float64,
        "fill_notional_usd": pl.Float64,
        "fee_bps": pl.Float64,
        "fee_amount": pl.Float64,
        "extra_slippage_bps": pl.Float64,
        "extra_slippage_amount": pl.Float64,
        "funding_amount_delta": pl.Float64,
        "liquidity_flag": pl.Utf8,
        "fill_price_source": pl.Utf8,
    }
    if not fills:
        return pl.DataFrame(schema=schema)
    return pl.from_dicts([fill.model_dump(mode="python") for fill in fills], schema=schema)


def trades_to_frame(trades: list[dict[str, object]]) -> pl.DataFrame:
    schema = {
        "entry_ts": pl.Datetime(time_zone="UTC"),
        "exit_ts": pl.Datetime(time_zone="UTC"),
        "symbol": pl.Utf8,
        "qty": pl.Float64,
        "entry_price": pl.Float64,
        "exit_price": pl.Float64,
        "gross_pnl": pl.Float64,
        "net_pnl": pl.Float64,
        "fees_paid": pl.Float64,
        "exit_reason": pl.Utf8,
    }
    if not trades:
        return pl.DataFrame(schema=schema)
    return pl.from_dicts(trades, schema=schema)


def equity_to_frame(rows: list[dict[str, object]]) -> pl.DataFrame:
    schema = {
        "event_ts": pl.Datetime(time_zone="UTC"),
        "cash_usd": pl.Float64,
        "position_qty": pl.Float64,
        "equity": pl.Float64,
        "unrealized_pnl": pl.Float64,
        "funding_pnl": pl.Float64,
        "is_evaluation": pl.Boolean,
        "session_type": pl.Utf8,
        "market_status": pl.Utf8,
    }
    if not rows:
        return pl.DataFrame(schema=schema)
    return pl.from_dicts(rows, schema=schema)
