from __future__ import annotations

from sis.backtest.engine.blocked import BlockedEvent
from sis.backtest.engine.config import BacktestConfig
from sis.backtest.engine.fill import next_fill_row_index
from sis.backtest.engine.order import Order
from sis.backtest.engine.portfolio import Portfolio
from sis.backtest.engine.run_loop import (
    BreakoutParameters,
    row_event_ts,
    row_index,
    signal_kind,
)
from sis.backtest.trade_xyz.cost_model import resolve_fee_bps
from sis.backtest.trade_xyz.gates import evaluate_entry_gate, evaluate_exit_gate


def _schedule_signal_order(
    *,
    rows: list[dict[str, object]],
    index: int,
    breakout: BreakoutParameters,
    config: BacktestConfig,
    portfolio: Portfolio,
    orders: list[Order],
    pending_orders: dict[int, Order],
    blocked: list[BlockedEvent],
) -> None:
    row = rows[index]
    signal = signal_kind(rows, index, breakout)
    fill_index = next_fill_row_index(signal_row_index=index, row_count=len(rows))
    actionable_signal_without_fill = (signal == "entry" and portfolio.position_qty == 0) or (
        signal == "exit" and portfolio.position_qty > 0
    )
    if fill_index is None and actionable_signal_without_fill:
        blocked.append(
            BlockedEvent(
                event_ts=row_event_ts(row),
                symbol=config.symbol,
                action=signal,
                reason="no_future_fill_row",
                strategy_id=config.strategy_id,
                signal_id=f"signal-{index}",
                row_index=row_index(row),
            )
        )
    elif fill_index is not None and signal == "exit" and portfolio.position_qty > 0:
        _schedule_exit_order(
            row=row,
            index=index,
            fill_index=fill_index,
            config=config,
            portfolio=portfolio,
            orders=orders,
            pending_orders=pending_orders,
        )
    elif fill_index is not None and signal == "entry" and portfolio.position_qty == 0:
        _schedule_entry_order(
            row=row,
            index=index,
            fill_index=fill_index,
            config=config,
            orders=orders,
            pending_orders=pending_orders,
            blocked=blocked,
        )


def _schedule_exit_order(
    *,
    row: dict[str, object],
    index: int,
    fill_index: int,
    config: BacktestConfig,
    portfolio: Portfolio,
    orders: list[Order],
    pending_orders: dict[int, Order],
) -> None:
    fee = resolve_fee_bps(
        row,
        fee_model_path=config.cost.fee_model_ref,
        fee_scenario=config.cost.fee_scenario,
    )
    gate = evaluate_exit_gate(
        row,
        position_is_open=True,
        exit_signal_exists=True,
        fee=fee,
    )
    if gate.allowed:
        order = Order(
            created_ts=row_event_ts(row),
            symbol=config.symbol,
            side="sell",
            position_effect="close",
            requested_notional_usd=portfolio.position_qty * portfolio.avg_entry_price,
            requested_qty=portfolio.position_qty,
            reduce_only=True,
            strategy_id=config.strategy_id,
            signal_id=f"signal-{index}",
        )
        orders.append(order)
        pending_orders[fill_index] = order


def _schedule_entry_order(
    *,
    row: dict[str, object],
    index: int,
    fill_index: int,
    config: BacktestConfig,
    orders: list[Order],
    pending_orders: dict[int, Order],
    blocked: list[BlockedEvent],
) -> None:
    fee = resolve_fee_bps(
        row,
        fee_model_path=config.cost.fee_model_ref,
        fee_scenario=config.cost.fee_scenario,
    )
    gate = evaluate_entry_gate(row, gates=config.gates, fee=fee)
    if gate.allowed:
        order = Order(
            created_ts=row_event_ts(row),
            symbol=config.symbol,
            side="buy",
            position_effect="open",
            requested_notional_usd=config.position_sizing.notional_usd,
            reduce_only=False,
            strategy_id=config.strategy_id,
            signal_id=f"signal-{index}",
        )
        orders.append(order)
        pending_orders[fill_index] = order
    else:
        for reason in gate.reasons:
            blocked.append(
                BlockedEvent(
                    event_ts=row_event_ts(row),
                    symbol=config.symbol,
                    action="entry",
                    reason=reason,
                    strategy_id=config.strategy_id,
                    signal_id=f"signal-{index}",
                    row_index=row_index(row),
                )
            )
