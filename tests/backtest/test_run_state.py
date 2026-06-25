from __future__ import annotations

from sis.backtest.engine.run_state import initialize_backtest_run_state


def test_initialize_backtest_run_state_sets_empty_containers_and_flat_portfolio() -> None:
    state = initialize_backtest_run_state(initial_cash_usd=10_000)

    assert state.portfolio.initial_cash_usd == 10_000
    assert state.portfolio.cash_usd == 10_000
    assert state.portfolio.position_qty == 0
    assert state.orders == []
    assert state.fills == []
    assert state.blocked == []
    assert state.equity_rows == []
    assert state.trades == []
    assert state.pending_orders == {}
    assert state.open_trade is None
    assert state.recorded_warnings == set()
    assert state.next_funding_event_index == 0


def test_initialize_backtest_run_state_does_not_share_mutable_containers() -> None:
    left = initialize_backtest_run_state(initial_cash_usd=10_000)
    right = initialize_backtest_run_state(initial_cash_usd=10_000)

    left.equity_rows.append({"equity": 10_000.0})
    left.trades.append({"net_pnl": 1.0})
    left.pending_orders[1] = object()  # type: ignore[assignment]
    left.recorded_warnings.add("warning")

    assert right.equity_rows == []
    assert right.trades == []
    assert right.pending_orders == {}
    assert right.recorded_warnings == set()
