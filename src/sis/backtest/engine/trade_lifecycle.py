from __future__ import annotations

from sis.backtest.engine.fill import Fill
from sis.backtest.engine.portfolio import Portfolio
from sis.backtest.engine.run_loop import as_float_value


def _apply_trade_lifecycle_fill(
    *,
    portfolio: Portfolio,
    fill: Fill,
    open_trade: dict[str, object] | None,
    exit_reason: str,
) -> tuple[Portfolio, dict[str, object] | None, dict[str, object] | None]:
    before = portfolio
    portfolio = portfolio.apply_fill(fill)
    if fill.position_effect == "open":
        return portfolio, _open_trade_row(fill), None
    if open_trade is None:
        return portfolio, None, None
    return (
        portfolio,
        None,
        _closed_trade_row(
            open_trade=open_trade,
            fill=fill,
            portfolio_before=before,
            portfolio_after=portfolio,
            exit_reason=exit_reason,
        ),
    )


def _open_trade_row(fill: Fill) -> dict[str, object]:
    return {
        "entry_ts": fill.event_ts,
        "symbol": fill.symbol,
        "qty": fill.qty,
        "entry_price": fill.fill_price,
        "entry_fee": fill.fee_amount,
    }


def _closed_trade_row(
    *,
    open_trade: dict[str, object],
    fill: Fill,
    portfolio_before: Portfolio,
    portfolio_after: Portfolio,
    exit_reason: str,
) -> dict[str, object]:
    entry_price = as_float_value(open_trade["entry_price"], field_name="entry_price")
    entry_fee = as_float_value(open_trade["entry_fee"], field_name="entry_fee")
    return {
        "entry_ts": open_trade["entry_ts"],
        "exit_ts": fill.event_ts,
        "symbol": fill.symbol,
        "qty": fill.qty,
        "entry_price": open_trade["entry_price"],
        "exit_price": fill.fill_price,
        "gross_pnl": (fill.fill_price - entry_price) * fill.qty,
        "net_pnl": portfolio_after.realized_pnl - portfolio_before.realized_pnl,
        "fees_paid": entry_fee + fill.fee_amount,
        "exit_reason": exit_reason,
    }
