from __future__ import annotations

from sis.backtest.engine.blocked import BlockedEvent
from sis.backtest.engine.config import BacktestConfig
from sis.backtest.engine.fill import Fill, resolve_market_like_fill_price
from sis.backtest.engine.order import Order
from sis.backtest.engine.portfolio import Portfolio
from sis.backtest.engine.run_loop import row_event_ts, row_index
from sis.backtest.trade_xyz.cost_model import calculate_market_like_fee, resolve_fee_bps
from sis.backtest.trade_xyz.gates import evaluate_close_fill_gate, evaluate_open_fill_gate


def _fill_order(
    *,
    order: Order,
    row: dict[str, object],
    config: BacktestConfig,
    portfolio: Portfolio,
) -> tuple[Fill | None, BlockedEvent | None]:
    side = "buy" if order.position_effect == "open" else "sell"
    price, source = resolve_market_like_fill_price(row, side=side)
    fee = resolve_fee_bps(
        row,
        fee_model_path=config.cost.fee_model_ref,
        fee_scenario=config.cost.fee_scenario,
    )
    if price is None or source is None or not fee.resolved or fee.taker_fee_bps is None:
        reason = "fill_price_unresolved" if price is None else "fee_unresolved"
        return None, BlockedEvent(
            event_ts=row_event_ts(row),
            symbol=config.symbol,
            action=order.position_effect,
            reason=reason,
            reason_detail=f"order_id={order.order_id}",
            strategy_id=config.strategy_id,
            signal_id=order.signal_id,
            row_index=row_index(row),
        )
    gate = (
        evaluate_open_fill_gate(
            row,
            gates=config.gates,
            fee=fee,
            fill_price_resolved=True,
        )
        if order.position_effect == "open"
        else evaluate_close_fill_gate(row, fee=fee, fill_price_resolved=True)
    )
    if not gate.allowed:
        return None, BlockedEvent(
            event_ts=row_event_ts(row),
            symbol=config.symbol,
            action=order.position_effect,
            reason=gate.reasons[0],
            reason_detail=";".join(gate.reasons),
            strategy_id=config.strategy_id,
            signal_id=order.signal_id,
            row_index=row_index(row),
        )
    qty = (
        order.requested_notional_usd / price
        if order.position_effect == "open"
        else portfolio.position_qty
    )
    notional = qty * price
    effective_taker_fee_bps = fee.taker_fee_bps * config.cost.fee_multiplier
    slippage = notional * config.execution.extra_slippage_bps / 10_000
    return Fill(
        fill_id=f"fill-{order.order_id}",
        order_id=order.order_id,
        event_ts=row_event_ts(row),
        symbol=config.symbol,
        side=side,
        position_effect=order.position_effect,
        qty=qty,
        fill_price=price,
        fill_notional_usd=notional,
        fee_bps=effective_taker_fee_bps,
        fee_amount=calculate_market_like_fee(
            fill_notional_usd=notional, taker_fee_bps=effective_taker_fee_bps
        ),
        fee_source=fee.source,
        extra_slippage_bps=config.execution.extra_slippage_bps,
        extra_slippage_amount=slippage,
        funding_amount_delta=0,
        liquidity_flag="taker",
        fill_price_source=source,
    ), None
