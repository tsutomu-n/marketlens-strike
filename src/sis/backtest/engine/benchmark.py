from __future__ import annotations

from typing import Any

import polars as pl

from sis.backtest.engine.config import BacktestConfig
from sis.backtest.engine.data_quality import apply_period_filter
from sis.backtest.engine.fill import resolve_market_like_fill_price
from sis.backtest.trade_xyz.cost_model import calculate_market_like_fee, resolve_fee_bps


def run_benchmarks(
    *, config: BacktestConfig, frame: pl.DataFrame
) -> tuple[dict[str, Any], pl.DataFrame]:
    filtered = apply_period_filter(frame, config=config)
    rows = filtered.to_dicts()
    if not rows:
        return {
            "cash_only": {"status": "unavailable"},
            "buy_and_hold_like": {"status": "unavailable"},
        }, pl.DataFrame(
            schema={
                "event_ts": pl.Datetime(time_zone="UTC"),
                "benchmark": pl.Utf8,
                "equity": pl.Float64,
            }
        )

    equity_rows: list[dict[str, object]] = []
    for row in rows:
        equity_rows.append(
            {
                "event_ts": row["event_ts"],
                "benchmark": "cash_only",
                "equity": config.initial_cash_usd,
            }
        )

    first = rows[0]
    last = rows[-1]
    entry_price, _entry_source = resolve_market_like_fill_price(first, side="buy")
    exit_price, _exit_source = resolve_market_like_fill_price(last, side="sell")
    fee = resolve_fee_bps(
        first,
        fee_model_path=config.cost.fee_model_ref,
        fee_scenario=config.cost.fee_scenario,
    )
    if entry_price is None or exit_price is None or not fee.resolved or fee.taker_fee_bps is None:
        return {
            "cash_only": {"status": "ok", "return": 0.0},
            "buy_and_hold_like": {"status": "unavailable"},
        }, pl.from_dicts(equity_rows)

    qty = config.position_sizing.notional_usd / entry_price
    entry_fee = calculate_market_like_fee(
        fill_notional_usd=qty * entry_price,
        taker_fee_bps=fee.taker_fee_bps * config.cost.fee_multiplier,
    )
    exit_fee = calculate_market_like_fee(
        fill_notional_usd=qty * exit_price,
        taker_fee_bps=fee.taker_fee_bps * config.cost.fee_multiplier,
    )
    ending_equity = (
        config.initial_cash_usd - qty * entry_price - entry_fee + qty * exit_price - exit_fee
    )
    for row in rows:
        mark = row.get("mid_price") or row.get("close") or entry_price
        equity_rows.append(
            {
                "event_ts": row["event_ts"],
                "benchmark": "buy_and_hold_like",
                "equity": config.initial_cash_usd
                - qty * entry_price
                - entry_fee
                + qty * float(mark),
            }
        )
    return {
        "cash_only": {"status": "ok", "return": 0.0},
        "buy_and_hold_like": {
            "status": "ok",
            "return": ending_equity / config.initial_cash_usd - 1,
        },
    }, pl.from_dicts(equity_rows)
