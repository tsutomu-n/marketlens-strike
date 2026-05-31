from __future__ import annotations

import polars as pl

from sis.backtest.engine.metrics import calculate_metrics


def test_metrics_include_session_and_market_status_breakdowns() -> None:
    equity = pl.DataFrame(
        {
            "equity": [10_000.0, 10_010.0],
            "session_type": ["regular", "overnight"],
            "market_status": ["open", "close_only"],
        }
    )

    metrics = calculate_metrics(
        initial_cash_usd=10_000,
        equity_curve=equity,
        trades=pl.DataFrame({"net_pnl": [10.0]}),
        fills=pl.DataFrame({"liquidity_flag": ["taker"], "fee_amount": [0.9]}),
        blocked_events=pl.DataFrame({"reason": []}, schema={"reason": pl.Utf8}),
        end_open_position_count=0,
        end_unrealized_pnl=0,
    )

    assert metrics["session_breakdown"] == {"overnight": 1, "regular": 1}
    assert metrics["market_status_breakdown"] == {"close_only": 1, "open": 1}
