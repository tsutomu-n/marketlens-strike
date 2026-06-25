from __future__ import annotations

from datetime import datetime, timezone

from sis.backtest.engine.config import (
    BacktestConfig,
    CostConfig,
    PeriodConfig,
    PositionSizingConfig,
)
from sis.backtest.engine.run_execution import execute_backtest_rows
from sis.backtest.engine.run_loop import BreakoutParameters
from sis.backtest.engine.run_state import initialize_backtest_run_state


def _config(*, cost: CostConfig | None = None) -> BacktestConfig:
    return BacktestConfig(
        run_id="run-execution",
        strategy_id="sp500_breakout_v0",
        symbol="SP500",
        timeframe="1h",
        period=PeriodConfig(
            evaluation_start_ts=datetime(2026, 1, 1, tzinfo=timezone.utc),
            evaluation_end_ts=datetime(2026, 1, 1, 6, tzinfo=timezone.utc),
        ),
        initial_cash_usd=10_000,
        position_sizing=PositionSizingConfig(notional_usd=1_000),
        cost=cost or CostConfig(),
    )


def _row(index: int, close: float, **overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "_row_index": index,
        "event_ts": datetime(2026, 1, 1, index, tzinfo=timezone.utc),
        "symbol": "SP500",
        "close": close,
        "best_bid": close - 0.1,
        "best_ask": close + 0.1,
        "oracle_price": 100.0,
        "taker_fee_bps": 9.0,
        "maker_fee_bps": 3.0,
        "market_status": "open",
        "is_tradable": True,
        "block_reasons": [],
        "is_evaluation": True,
        "session_type": "regular",
    }
    row.update(overrides)
    return row


def _breakout_rows(**row3_overrides: object) -> list[dict[str, object]]:
    return [
        _row(0, 100.0),
        _row(1, 101.0),
        _row(2, 103.0),
        _row(3, 102.0, **row3_overrides),
        _row(4, 99.0),
        _row(5, 98.0),
    ]


def test_execute_backtest_rows_fills_pending_order_before_quote_row_funding() -> None:
    state = execute_backtest_rows(
        rows=_breakout_rows(funding_rate=0.01, is_funding_event=True),
        funding_event_rows=[],
        state=initialize_backtest_run_state(initial_cash_usd=10_000),
        config=_config(cost=CostConfig(funding_policy="fixture_hourly_v0")),
        breakout=BreakoutParameters(entry_lookback=2, exit_lookback=2),
    )

    assert [fill.event_ts for fill in state.fills] == [
        datetime(2026, 1, 1, 3, tzinfo=timezone.utc),
        datetime(2026, 1, 1, 5, tzinfo=timezone.utc),
    ]
    assert state.fills[0].position_effect == "open"
    assert state.portfolio.funding_pnl < 0
    assert state.equity_rows[3]["funding_pnl"] < 0
    assert len(state.equity_rows) == 6


def test_execute_backtest_rows_applies_external_funding_after_pending_fill() -> None:
    state = execute_backtest_rows(
        rows=_breakout_rows(funding_rate=0.99, is_funding_event=False),
        funding_event_rows=[
            {
                "event_ts": datetime(2026, 1, 1, 3, tzinfo=timezone.utc),
                "funding_rate": 0.01,
                "oracle_price": 100.0,
            }
        ],
        state=initialize_backtest_run_state(initial_cash_usd=10_000),
        config=_config(cost=CostConfig(funding_policy="fixture_hourly_v0")),
        breakout=BreakoutParameters(entry_lookback=2, exit_lookback=2),
    )

    assert state.next_funding_event_index == 1
    assert state.portfolio.funding_pnl < 0
    assert state.equity_rows[3]["funding_pnl"] < 0
    assert state.blocked == []
