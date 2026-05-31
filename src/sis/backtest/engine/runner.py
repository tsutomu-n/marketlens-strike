from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

import polars as pl
from pydantic import BaseModel

from sis.backtest.engine.blocked import BlockedEvent, blocked_events_to_frame
from sis.backtest.engine.benchmark import run_benchmarks
from sis.backtest.engine.config import BacktestConfig
from sis.backtest.engine.data_quality import apply_period_filter, evaluate_data_quality
from sis.backtest.engine.fill import Fill, next_fill_row_index, resolve_market_like_fill_price
from sis.backtest.engine.hashing import config_hash, input_schema_hash
from sis.backtest.engine.manifest import build_data_manifest
from sis.backtest.engine.metrics import calculate_metrics
from sis.backtest.engine.parameter_sweep import default_breakout_parameter_grid
from sis.backtest.engine.report import render_backtest_html, render_backtest_markdown
from sis.backtest.engine.scenarios import default_scenarios
from sis.backtest.engine.charts import render_line_svg, render_placeholder_svg
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
class BreakoutParameters:
    entry_lookback: int = 20
    exit_lookback: int = 10


@dataclass(frozen=True)
class BacktestRunResult:
    run_dir: Path
    metrics: dict[str, object]


def _write_json(path: Path, payload: BaseModel | dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = payload.model_dump(mode="json") if isinstance(payload, BaseModel) else payload
    path.write_text(
        json.dumps(data, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )


def _orders_to_frame(orders: list[Order]) -> pl.DataFrame:
    schema = {
        "order_id": pl.Utf8,
        "client_order_id": pl.Utf8,
        "created_ts": pl.Datetime(time_zone="UTC"),
        "symbol": pl.Utf8,
        "side": pl.Utf8,
        "position_effect": pl.Utf8,
        "order_type": pl.Utf8,
        "requested_notional_usd": pl.Float64,
        "requested_qty": pl.Float64,
        "limit_price": pl.Null,
        "reduce_only": pl.Boolean,
        "strategy_id": pl.Utf8,
        "signal_id": pl.Utf8,
    }
    if not orders:
        return pl.DataFrame(schema=schema)
    return pl.from_dicts([order.model_dump(mode="python") for order in orders], schema=schema)


def _fills_to_frame(fills: list[Fill]) -> pl.DataFrame:
    schema = {
        "fill_id": pl.Utf8,
        "order_id": pl.Utf8,
        "event_ts": pl.Datetime(time_zone="UTC"),
        "symbol": pl.Utf8,
        "side": pl.Utf8,
        "position_effect": pl.Utf8,
        "qty": pl.Float64,
        "fill_price": pl.Float64,
        "fill_notional_usd": pl.Float64,
        "fee_bps": pl.Float64,
        "fee_amount": pl.Float64,
        "extra_slippage_bps": pl.Float64,
        "extra_slippage_amount": pl.Float64,
        "funding_amount_delta": pl.Float64,
        "liquidity_flag": pl.Utf8,
        "fill_price_source": pl.Utf8,
    }
    if not fills:
        return pl.DataFrame(schema=schema)
    return pl.from_dicts([fill.model_dump(mode="python") for fill in fills], schema=schema)


def _trades_to_frame(trades: list[dict[str, object]]) -> pl.DataFrame:
    schema = {
        "entry_ts": pl.Datetime(time_zone="UTC"),
        "exit_ts": pl.Datetime(time_zone="UTC"),
        "symbol": pl.Utf8,
        "qty": pl.Float64,
        "entry_price": pl.Float64,
        "exit_price": pl.Float64,
        "gross_pnl": pl.Float64,
        "net_pnl": pl.Float64,
        "fees_paid": pl.Float64,
        "exit_reason": pl.Utf8,
    }
    if not trades:
        return pl.DataFrame(schema=schema)
    return pl.from_dicts(trades, schema=schema)


def _equity_to_frame(rows: list[dict[str, object]]) -> pl.DataFrame:
    schema = {
        "event_ts": pl.Datetime(time_zone="UTC"),
        "cash_usd": pl.Float64,
        "position_qty": pl.Float64,
        "equity": pl.Float64,
        "unrealized_pnl": pl.Float64,
        "funding_pnl": pl.Float64,
        "is_evaluation": pl.Boolean,
        "session_type": pl.Utf8,
        "market_status": pl.Utf8,
    }
    if not rows:
        return pl.DataFrame(schema=schema)
    return pl.from_dicts(rows, schema=schema)


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


def _signal_kind(
    rows: list[dict[str, object]], index: int, breakout: BreakoutParameters
) -> str | None:
    close = rows[index].get("close")
    if not isinstance(close, int | float):
        return None
    if index >= breakout.entry_lookback:
        previous = [
            row.get("close")
            for row in rows[index - breakout.entry_lookback : index]
            if isinstance(row.get("close"), int | float)
        ]
        if previous and close > max(previous):
            return "entry"
    if index >= breakout.exit_lookback:
        previous = [
            row.get("close")
            for row in rows[index - breakout.exit_lookback : index]
            if isinstance(row.get("close"), int | float)
        ]
        if previous and close < min(previous):
            return "exit"
    return None


def _row_event_ts(row: dict[str, object]) -> datetime:
    value = row["event_ts"]
    if not isinstance(value, datetime):
        raise ValueError(f"event_ts must be datetime, got {type(value).__name__}")
    return value


def _row_index(row: dict[str, object]) -> int:
    value = row["_row_index"]
    if not isinstance(value, int):
        raise ValueError(f"_row_index must be int, got {type(value).__name__}")
    return value


def _as_float_value(value: Any, *, field_name: str) -> float:
    if not isinstance(value, int | float):
        raise ValueError(f"{field_name} must be numeric")
    return float(value)


def _optional_float(value: object) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


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
            event_ts=_row_event_ts(row),
            symbol=config.symbol,
            action=order.position_effect,
            reason=reason,
            reason_detail=f"order_id={order.order_id}",
            strategy_id=config.strategy_id,
            signal_id=order.signal_id,
            row_index=_row_index(row),
        )
    qty = (
        order.requested_notional_usd / price
        if order.position_effect == "open"
        else portfolio.position_qty
    )
    notional = qty * price
    slippage = notional * config.execution.extra_slippage_bps / 10_000
    return Fill(
        fill_id=f"fill-{order.order_id}",
        order_id=order.order_id,
        event_ts=_row_event_ts(row),
        symbol=config.symbol,
        side=side,
        position_effect=order.position_effect,
        qty=qty,
        fill_price=price,
        fill_notional_usd=notional,
        fee_bps=fee.taker_fee_bps,
        fee_amount=calculate_market_like_fee(
            fill_notional_usd=notional, taker_fee_bps=fee.taker_fee_bps
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
                                - _as_float_value(
                                    open_trade["entry_price"], field_name="entry_price"
                                )
                            )
                            * fill.qty,
                            "net_pnl": portfolio.realized_pnl - before.realized_pnl,
                            "fees_paid": _as_float_value(
                                open_trade["entry_fee"], field_name="entry_fee"
                            )
                            + fill.fee_amount,
                            "exit_reason": "signal_exit",
                        }
                    )
                    open_trade = None

        signal = _signal_kind(rows, index, breakout)
        fill_index = next_fill_row_index(signal_row_index=index, row_count=len(rows))
        if fill_index is not None and signal == "exit" and portfolio.position_qty > 0:
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
                    created_ts=_row_event_ts(row),
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
                    created_ts=_row_event_ts(row),
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
                            event_ts=_row_event_ts(row),
                            symbol=config.symbol,
                            action="entry",
                            reason=reason,
                            strategy_id=config.strategy_id,
                            signal_id=f"signal-{index}",
                            row_index=_row_index(row),
                        )
                    )

        if portfolio.position_qty > 0:
            funding_amount, funding_warning = calculate_v0_funding_amount(
                policy=config.cost.funding_policy,
                position_qty=portfolio.position_qty,
                oracle_price=_optional_float(row.get("oracle_price")),
                funding_rate=_optional_float(row.get("funding_rate")),
                is_funding_event=bool(row.get("is_funding_event")),
                event_ts=_row_event_ts(row),
            )
            if funding_amount:
                portfolio = portfolio.apply_funding(funding_amount)
            if funding_warning is not None and config.cost.funding_policy == "fixture_hourly_v0":
                blocked.append(
                    BlockedEvent(
                        event_ts=_row_event_ts(row),
                        symbol=config.symbol,
                        action="funding",
                        reason=funding_warning,
                        strategy_id=config.strategy_id,
                        signal_id=None,
                        row_index=_row_index(row),
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
                "event_ts": _row_event_ts(row),
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
            created_ts=_row_event_ts(last_row),
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
                            - _as_float_value(open_trade["entry_price"], field_name="entry_price")
                        )
                        * fill.qty,
                        "net_pnl": portfolio.realized_pnl - before.realized_pnl,
                        "fees_paid": _as_float_value(
                            open_trade["entry_fee"], field_name="entry_fee"
                        )
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

    orders_frame = _orders_to_frame(orders)
    fills_frame = _fills_to_frame(fills)
    trades_frame = _trades_to_frame(trades)
    blocked_frame = blocked_events_to_frame(blocked)
    equity_frame = _equity_to_frame(equity_rows)
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
    run_dir.mkdir(parents=True, exist_ok=True)
    _write_json(run_dir / "config.json", config)
    _write_json(run_dir / "data_quality.json", quality)
    _write_json(run_dir / "data_manifest.json", manifest)
    _write_json(run_dir / "metrics.json", metrics)
    _write_json(run_dir / "benchmark_results.json", benchmark_results)
    _write_json(
        run_dir / "scenario_summary.json",
        {
            "scenarios": [row["scenario"] for row in scenario_rows],
            "base_only_edge_warning": True,
        },
    )
    _write_json(run_dir / "split_results.json", split_summary)
    _write_json(
        run_dir / "parameter_summary.json",
        {
            "grid_size": len(parameter_rows),
            "best_parameter_is_in_sample_only": True,
        },
    )
    _write_json(
        run_dir / "candidate_result.json",
        {
            "run_id": config.run_id,
            "strategy_id": config.strategy_id,
            "symbol": config.symbol,
            "metrics": metrics,
            "data_manifest": "data_manifest.json",
        },
    )
    _write_json(
        run_dir / "backtest_run.json",
        {
            "run_id": config.run_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "strategy_id": config.strategy_id,
            "symbol": config.symbol,
            "timeframe": config.timeframe,
            "warmup_start_ts": config.period.warmup_start_ts.isoformat()
            if config.period.warmup_start_ts
            else None,
            "evaluation_start_ts": config.period.evaluation_start_ts.isoformat(),
            "evaluation_end_ts": config.period.evaluation_end_ts.isoformat(),
            "input_data_ref": input_data_ref,
            "config_hash": config_hash(config),
            "input_schema_hash": input_schema_hash(normalized),
            "fee_model_ref": config.cost.fee_model_ref,
            "funding_policy": config.cost.funding_policy,
            "fill_model": config.execution.fill_model,
            "leverage_mode": config.leverage.mode,
            "no_live_order": True,
            "wallet_used": False,
            "exchange_write_used": False,
        },
    )
    (run_dir / "config_hash.txt").write_text(config_hash(config) + "\n", encoding="utf-8")
    (run_dir / "input_schema_hash.txt").write_text(
        input_schema_hash(normalized) + "\n", encoding="utf-8"
    )
    orders_frame.write_parquet(run_dir / "orders.parquet")
    fills_frame.write_parquet(run_dir / "fills.parquet")
    trades_frame.write_parquet(run_dir / "trades.parquet")
    blocked_frame.write_parquet(run_dir / "blocked_events.parquet")
    equity_frame.write_parquet(run_dir / "equity_curve.parquet")
    benchmark_equity.write_parquet(run_dir / "benchmark_equity_curve.parquet")
    pl.from_dicts(scenario_rows).write_parquet(run_dir / "scenario_results.parquet")
    pl.from_dicts(parameter_rows).write_parquet(run_dir / "parameter_results.parquet")
    artifacts = {
        "metrics": "metrics.json",
        "data_manifest": "data_manifest.json",
        "orders": "orders.parquet",
        "fills": "fills.parquet",
        "trades": "trades.parquet",
        "equity_curve": "equity_curve.parquet",
    }
    markdown = render_backtest_markdown(
        metrics=metrics,
        artifacts=artifacts,
        warnings=[
            "v0.1 long-only single-symbol market-like taker fill",
            "best_parameter_is_in_sample_only: true",
            "scenario_results show fee/slippage sensitivity from base run costs",
        ],
    )
    (run_dir / "backtest_report.md").write_text(markdown, encoding="utf-8")
    (run_dir / "backtest_report.html").write_text(render_backtest_html(markdown), encoding="utf-8")
    charts_dir = run_dir / "charts"
    charts_dir.mkdir(exist_ok=True)
    equity_values = [float(value) for value in equity_frame.get_column("equity").to_list()]
    peak = None
    drawdowns: list[float] = []
    for value in equity_values:
        peak = value if peak is None else max(peak, value)
        drawdowns.append(value / peak - 1 if peak else 0.0)
    chart_svgs = {
        "equity_curve": render_line_svg(title="Equity Curve", values=equity_values),
        "drawdown": render_line_svg(title="Drawdown", values=drawdowns),
        "trade_pnl_histogram": render_placeholder_svg(title="Trade PnL Histogram"),
        "cumulative_costs": render_line_svg(
            title="Cumulative Costs",
            values=[
                float(row.get("fee_amount") or 0) + float(row.get("extra_slippage_amount") or 0)
                for row in fills_frame.to_dicts()
            ],
        ),
        "blocked_reasons": render_placeholder_svg(title="Blocked Reasons"),
        "session_breakdown": render_placeholder_svg(title="Session Breakdown"),
    }
    for name, svg in chart_svgs.items():
        (charts_dir / f"{name}.svg").write_text(svg, encoding="utf-8")
    charts_data_dir = run_dir / "charts_data"
    charts_data_dir.mkdir(exist_ok=True)
    charts_payloads = {
        "equity_curve": {"rows": equity_frame.to_dicts()},
        "drawdown": {"rows": equity_frame.select(["event_ts", "equity"]).to_dicts()},
        "trades": {"rows": trades_frame.to_dicts()},
        "blocked_reasons": {"rows": blocked_frame.to_dicts()},
    }
    for name, payload in charts_payloads.items():
        _write_json(
            charts_data_dir / f"{name}.json", {"name": name, "run_id": config.run_id, **payload}
        )
    return BacktestRunResult(run_dir=run_dir, metrics=metrics)
