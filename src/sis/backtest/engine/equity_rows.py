from __future__ import annotations

from sis.backtest.engine.portfolio import Portfolio
from sis.backtest.engine.run_loop import row_event_ts


def _equity_row(*, row: dict[str, object], portfolio: Portfolio) -> dict[str, object]:
    mark_price = row.get("mid_price") or row.get("close") or portfolio.avg_entry_price
    mark_price_is_numeric = isinstance(mark_price, int | float)
    unrealized = (
        (float(mark_price) - portfolio.avg_entry_price) * portfolio.position_qty
        if portfolio.position_qty > 0 and mark_price_is_numeric
        else 0.0
    )
    return {
        "event_ts": row_event_ts(row),
        "cash_usd": portfolio.cash_usd,
        "position_qty": portfolio.position_qty,
        "equity": portfolio.cash_usd
        + (portfolio.position_qty * float(mark_price) if mark_price_is_numeric else 0.0),
        "unrealized_pnl": unrealized,
        "funding_pnl": portfolio.funding_pnl,
        "is_evaluation": row["is_evaluation"],
        "session_type": str(row.get("session_type") or "unknown"),
        "market_status": str(row.get("market_status") or "unknown"),
    }
