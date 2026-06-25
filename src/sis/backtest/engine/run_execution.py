from __future__ import annotations

from sis.backtest.engine.config import BacktestConfig
from sis.backtest.engine.equity_rows import _equity_row
from sis.backtest.engine.funding import (
    apply_external_funding_after_loop,
    apply_external_funding_before_signal,
    apply_quote_row_funding_after_signal,
)
from sis.backtest.engine.order_scheduling import _schedule_signal_order
from sis.backtest.engine.pending_fill_execution import _apply_pending_order_fill
from sis.backtest.engine.run_loop import BreakoutParameters
from sis.backtest.engine.run_state import BacktestRunState


def execute_backtest_rows(
    *,
    rows: list[dict[str, object]],
    funding_event_rows: list[dict[str, object]],
    state: BacktestRunState,
    config: BacktestConfig,
    breakout: BreakoutParameters,
) -> BacktestRunState:
    for index, row in enumerate(rows):
        order = state.pending_orders.pop(index, None)
        if order is not None:
            state.portfolio, state.open_trade = _apply_pending_order_fill(
                order=order,
                row=row,
                config=config,
                portfolio=state.portfolio,
                open_trade=state.open_trade,
                fills=state.fills,
                blocked=state.blocked,
                trades=state.trades,
            )

        state.next_funding_event_index, state.portfolio = apply_external_funding_before_signal(
            events=funding_event_rows,
            next_event_index=state.next_funding_event_index,
            row=row,
            config=config,
            portfolio=state.portfolio,
            blocked=state.blocked,
            recorded_warnings=state.recorded_warnings,
        )

        _schedule_signal_order(
            rows=rows,
            index=index,
            breakout=breakout,
            config=config,
            portfolio=state.portfolio,
            orders=state.orders,
            pending_orders=state.pending_orders,
            blocked=state.blocked,
        )

        state.portfolio = apply_quote_row_funding_after_signal(
            row=row,
            has_external_funding_events=bool(funding_event_rows),
            config=config,
            portfolio=state.portfolio,
            blocked=state.blocked,
            recorded_warnings=state.recorded_warnings,
        )

        state.equity_rows.append(_equity_row(row=row, portfolio=state.portfolio))

    state.next_funding_event_index, state.portfolio = apply_external_funding_after_loop(
        events=funding_event_rows,
        next_event_index=state.next_funding_event_index,
        config=config,
        portfolio=state.portfolio,
        blocked=state.blocked,
        recorded_warnings=state.recorded_warnings,
    )
    return state
