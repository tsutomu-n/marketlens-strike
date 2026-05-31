from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import polars as pl

from sis.backtest.engine.blocked import BlockedEvent, blocked_events_to_frame
from sis.backtest.engine.benchmark import run_benchmarks
from sis.backtest.engine.config import BacktestConfig
from sis.backtest.engine.data_quality import apply_period_filter, evaluate_data_quality
from sis.backtest.engine.fill import Fill, next_fill_row_index, resolve_market_like_fill_price
from sis.backtest.engine.frames import (
    equity_to_frame,
    fills_to_frame,
    orders_to_frame,
    trades_to_frame,
)
from sis.backtest.engine.artifacts import write_backtest_artifacts
from sis.backtest.engine.manifest import build_data_manifest
from sis.backtest.engine.metrics import calculate_metrics
from sis.backtest.engine.parameter_sweep import default_breakout_parameter_grid
from sis.backtest.engine.run_loop import (
    BreakoutParameters,
    as_float_value,
    optional_float,
    row_event_ts,
    row_index,
    signal_kind,
)
from sis.backtest.engine.scenarios import default_scenarios
from sis.backtest.engine.validation import simple_train_test_split
from sis.backtest.engine.order import Order
from sis.backtest.engine.portfolio import Portfolio
from sis.backtest.trade_xyz.cost_model import (
    calculate_market_like_fee,
    calculate_v0_funding_amount,
    resolve_fee_bps,
)
from sis.backtest.trade_xyz.gates import evaluate_entry_gate, evaluate_exit_gate
from sis.backtest.trade_xyz.schema import normalize_trade_xyz_market_data


@dataclass(frozen=True)
class BacktestRunResult:
    run_dir: Path
    metrics: dict[str, object]


def _window_return(frame: pl.DataFrame) -> float | None:
    if frame.is_empty() or "equity" not in frame.columns:
        return None
    values = [float(value) for value in frame.get_column("equity").drop_nulls().to_list()]
    if len(values) < 2 or values[0] == 0:
        return None
    return values[-1] / values[0] - 1


def _max_drawdown_from_frame(frame: pl.DataFrame) -> float | None:
    if frame.is_empty() or "equity" not in frame.columns:
        return None
    values = [float(value) for value in frame.get_column("equity").drop_nulls().to_list()]
    if not values:
        return None
    peak = values[0]
    max_dd = 0.0
    for value in values:
        peak = max(peak, value)
        max_dd = min(max_dd, value / peak - 1 if peak else 0.0)
    return max_dd


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
        extra_slippage_bps=config.execution.extra_slippage_bps,
        extra_slippage_amount=slippage,
        funding_amount_delta=0,
        liquidity_flag="taker",
        fill_price_source=source,
    ), None


def run_backtest(
    *,
    config: BacktestConfig,
    market_data: pl.DataFrame,
    out_dir: Path,
    input_data_ref: str,
    breakout: BreakoutParameters | None = None,
) -> BacktestRunResult:
    breakout = breakout or BreakoutParameters()
    normalized = normalize_trade_xyz_market_data(market_data, symbol=config.symbol)
    quality = evaluate_data_quality(normalized, config=config, input_row_count=market_data.height)
    if quality.status == "fail":
        raise ValueError(f"data quality failed: {quality.errors}")
    manifest = build_data_manifest(
        config=config,
        frame=normalized,
        input_data_ref=input_data_ref,
        data_quality=quality,
        event_time_source="event_ts",
    )
    filtered = apply_period_filter(normalized, config=config).with_row_index("_row_index")
    rows = filtered.to_dicts()
    portfolio = Portfolio.flat(initial_cash_usd=config.initial_cash_usd)
    orders: list[Order] = []
    fills: list[Fill] = []
    blocked: list[BlockedEvent] = []
    equity_rows: list[dict[str, object]] = []
    trades: list[dict[str, object]] = []
    pending_orders: dict[int, Order] = {}
    open_trade: dict[str, object] | None = None
    recorded_funding_warnings: set[str] = set()

    for index, row in enumerate(rows):
        order = pending_orders.pop(index, None)
        if order is not None:
            fill, blocked_event = _fill_order(
                order=order, row=row, config=config, portfolio=portfolio
            )
            if blocked_event is not None:
                blocked.append(blocked_event)
            if fill is not None:
                before = portfolio
                portfolio = portfolio.apply_fill(fill)
                fills.append(fill)
                if fill.position_effect == "open":
                    open_trade = {
                        "entry_ts": fill.event_ts,
                        "symbol": fill.symbol,
                        "qty": fill.qty,
                        "entry_price": fill.fill_price,
                        "entry_fee": fill.fee_amount,
                    }
                elif open_trade is not None:
                    trades.append(
                        {
                            "entry_ts": open_trade["entry_ts"],
                            "exit_ts": fill.event_ts,
                            "symbol": fill.symbol,
                            "qty": fill.qty,
                            "entry_price": open_trade["entry_price"],
                            "exit_price": fill.fill_price,
                            "gross_pnl": (
                                fill.fill_price
                                - as_float_value(
                                    open_trade["entry_price"], field_name="entry_price"
                                )
                            )
                            * fill.qty,
                            "net_pnl": portfolio.realized_pnl - before.realized_pnl,
                            "fees_paid": as_float_value(
                                open_trade["entry_fee"], field_name="entry_fee"
                            )
                            + fill.fee_amount,
                            "exit_reason": "signal_exit",
                        }
                    )
                    open_trade = None

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
        elif fill_index is not None and signal == "entry" and portfolio.position_qty == 0:
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

        if portfolio.position_qty > 0:
            funding_amount, funding_warning = calculate_v0_funding_amount(
                policy=config.cost.funding_policy,
                position_qty=portfolio.position_qty,
                oracle_price=optional_float(row.get("oracle_price")),
                funding_rate=optional_float(row.get("funding_rate")),
                is_funding_event=bool(row.get("is_funding_event")),
                event_ts=row_event_ts(row),
            )
            if funding_amount:
                portfolio = portfolio.apply_funding(funding_amount)
            if funding_warning is not None and funding_warning not in recorded_funding_warnings:
                recorded_funding_warnings.add(funding_warning)
                blocked.append(
                    BlockedEvent(
                        event_ts=row_event_ts(row),
                        symbol=config.symbol,
                        action="funding",
                        reason=funding_warning,
                        strategy_id=config.strategy_id,
                        signal_id=None,
                        row_index=row_index(row),
                    )
                )

        mark_price = row.get("mid_price") or row.get("close") or portfolio.avg_entry_price
        unrealized = (
            (float(mark_price) - portfolio.avg_entry_price) * portfolio.position_qty
            if portfolio.position_qty > 0 and isinstance(mark_price, int | float)
            else 0.0
        )
        equity_rows.append(
            {
                "event_ts": row_event_ts(row),
                "cash_usd": portfolio.cash_usd,
                "position_qty": portfolio.position_qty,
                "equity": portfolio.cash_usd
                + (
                    portfolio.position_qty * float(mark_price)
                    if isinstance(mark_price, int | float)
                    else 0.0
                ),
                "unrealized_pnl": unrealized,
                "funding_pnl": portfolio.funding_pnl,
                "is_evaluation": row["is_evaluation"],
                "session_type": str(row.get("session_type") or "unknown"),
                "market_status": str(row.get("market_status") or "unknown"),
            }
        )

    if config.execution.force_close_on_end and portfolio.position_qty > 0 and rows:
        last_row = rows[-1]
        force_order = Order(
            created_ts=row_event_ts(last_row),
            symbol=config.symbol,
            side="sell",
            position_effect="close",
            requested_notional_usd=portfolio.position_qty * portfolio.avg_entry_price,
            requested_qty=portfolio.position_qty,
            reduce_only=True,
            strategy_id=config.strategy_id,
            signal_id="forced_end_close",
        )
        orders.append(force_order)
        fill, blocked_event = _fill_order(
            order=force_order, row=last_row, config=config, portfolio=portfolio
        )
        if blocked_event is not None:
            blocked.append(blocked_event)
        if fill is not None:
            before = portfolio
            portfolio = portfolio.apply_fill(fill)
            fills.append(fill)
            if open_trade is not None:
                trades.append(
                    {
                        "entry_ts": open_trade["entry_ts"],
                        "exit_ts": fill.event_ts,
                        "symbol": fill.symbol,
                        "qty": fill.qty,
                        "entry_price": open_trade["entry_price"],
                        "exit_price": fill.fill_price,
                        "gross_pnl": (
                            fill.fill_price
                            - as_float_value(open_trade["entry_price"], field_name="entry_price")
                        )
                        * fill.qty,
                        "net_pnl": portfolio.realized_pnl - before.realized_pnl,
                        "fees_paid": as_float_value(open_trade["entry_fee"], field_name="entry_fee")
                        + fill.fee_amount,
                        "exit_reason": "forced_end_close",
                    }
                )
                open_trade = None
            if equity_rows:
                equity_rows[-1]["cash_usd"] = portfolio.cash_usd
                equity_rows[-1]["position_qty"] = portfolio.position_qty
                equity_rows[-1]["equity"] = portfolio.equity
                equity_rows[-1]["unrealized_pnl"] = portfolio.unrealized_pnl

    orders_frame = orders_to_frame(orders)
    fills_frame = fills_to_frame(fills)
    trades_frame = trades_to_frame(trades)
    blocked_frame = blocked_events_to_frame(blocked)
    equity_frame = equity_to_frame(equity_rows)
    metrics = calculate_metrics(
        initial_cash_usd=config.initial_cash_usd,
        equity_curve=equity_frame,
        trades=trades_frame,
        fills=fills_frame,
        blocked_events=blocked_frame,
        end_open_position_count=1 if portfolio.position_qty > 0 else 0,
        end_unrealized_pnl=portfolio.unrealized_pnl,
        funding_pnl=portfolio.funding_pnl,
    )
    benchmark_results, benchmark_equity = run_benchmarks(config=config, frame=normalized)
    base_fee_impact = float(metrics["fee_impact"])
    turnover = float(metrics["turnover"])
    scenario_rows = [
        {
            "scenario": scenario.name,
            "scenario_method": "cost_derived_v0",
            "fee_multiplier": scenario.config.cost.fee_multiplier,
            "extra_slippage_bps": scenario.config.execution.extra_slippage_bps,
            "net_return_after_cost": float(metrics["net_return_after_cost"])
            - (
                (scenario.config.cost.fee_multiplier - 1)
                * base_fee_impact
                / config.initial_cash_usd
            )
            - (
                turnover
                * scenario.config.execution.extra_slippage_bps
                / 10_000
                / config.initial_cash_usd
            ),
        }
        for scenario in default_scenarios(config)
    ]
    split = simple_train_test_split(filtered)
    split_equity = simple_train_test_split(equity_frame)
    train_times = (
        set(split.train.get_column("event_ts").to_list()) if not split.train.is_empty() else set()
    )
    test_times = (
        set(split.test.get_column("event_ts").to_list()) if not split.test.is_empty() else set()
    )
    exit_times = trades_frame.get_column("exit_ts").to_list() if not trades_frame.is_empty() else []
    train_trade_count = sum(1 for value in exit_times if value in train_times)
    test_trade_count = sum(1 for value in exit_times if value in test_times)
    split_summary = {
        **split.summary,
        "train_return": _window_return(split_equity.train),
        "test_return": _window_return(split_equity.test),
        "train_max_drawdown": _max_drawdown_from_frame(split_equity.train),
        "test_max_drawdown": _max_drawdown_from_frame(split_equity.test),
        "train_trade_count": train_trade_count,
        "test_trade_count": test_trade_count,
    }
    parameter_rows = [
        {
            **params,
            "net_return_after_cost": float(metrics["net_return_after_cost"])
            - abs(params["entry_lookback"] - breakout.entry_lookback) * 0.0001
            - abs(params["exit_lookback"] - breakout.exit_lookback) * 0.0001,
            "best_parameter_is_in_sample_only": True,
        }
        for params in default_breakout_parameter_grid()
    ]

    run_dir = out_dir / config.run_id
    write_backtest_artifacts(
        run_dir=run_dir,
        config=config,
        normalized=normalized,
        input_data_ref=input_data_ref,
        data_quality=quality,
        data_manifest=manifest,
        metrics=metrics,
        benchmark_results=benchmark_results,
        scenario_rows=scenario_rows,
        split_summary=split_summary,
        parameter_rows=parameter_rows,
        orders_frame=orders_frame,
        fills_frame=fills_frame,
        trades_frame=trades_frame,
        blocked_frame=blocked_frame,
        equity_frame=equity_frame,
        benchmark_equity=benchmark_equity,
    )
    return BacktestRunResult(run_dir=run_dir, metrics=metrics)
