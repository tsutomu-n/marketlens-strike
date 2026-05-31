from __future__ import annotations

import math
from typing import Any

import polars as pl


def _float_column(frame: pl.DataFrame, column: str) -> list[float]:
    if column not in frame.columns or frame.is_empty():
        return []
    return [float(value) for value in frame.get_column(column).drop_nulls().to_list()]


def _max_drawdown(equity_values: list[float]) -> float:
    peak = -math.inf
    max_dd = 0.0
    for value in equity_values:
        peak = max(peak, value)
        if peak > 0:
            max_dd = min(max_dd, value / peak - 1)
    return max_dd


def _blocked_reason_counts(blocked_events: pl.DataFrame) -> dict[str, int]:
    if "reason" not in blocked_events.columns or blocked_events.is_empty():
        return {}
    rows = blocked_events.group_by("reason").len().sort("reason").to_dicts()
    return {str(row["reason"]): int(row["len"]) for row in rows}


def _value_counts(frame: pl.DataFrame, column: str) -> dict[str, int]:
    if column not in frame.columns or frame.is_empty():
        return {}
    rows = frame.group_by(column).len().sort(column).to_dicts()
    return {str(row[column]): int(row["len"]) for row in rows if row[column] is not None}


def calculate_metrics(
    *,
    initial_cash_usd: float,
    equity_curve: pl.DataFrame,
    trades: pl.DataFrame,
    fills: pl.DataFrame,
    blocked_events: pl.DataFrame,
    end_open_position_count: int,
    end_unrealized_pnl: float,
    funding_pnl: float | None = None,
) -> dict[str, Any]:
    equity_values = _float_column(equity_curve, "equity")
    ending_equity = equity_values[-1] if equity_values else initial_cash_usd
    trade_pnls = _float_column(trades, "net_pnl")
    winners = [value for value in trade_pnls if value > 0]
    losers = [value for value in trade_pnls if value < 0]
    fee_amounts = _float_column(fills, "fee_amount")
    slippage_amounts = _float_column(fills, "extra_slippage_amount")
    funding_amounts = _float_column(fills, "funding_amount_delta")
    funding_impact = funding_pnl if funding_pnl is not None else sum(funding_amounts)
    taker_fills = (
        int(fills.filter(pl.col("liquidity_flag") == "taker").height)
        if "liquidity_flag" in fills.columns
        else 0
    )
    fill_count = fills.height
    return {
        "net_return_after_cost": ending_equity / initial_cash_usd - 1,
        "total_return": ending_equity / initial_cash_usd - 1,
        "max_drawdown": _max_drawdown(equity_values),
        "trade_count": len(trade_pnls),
        "win_rate": len(winners) / len(trade_pnls) if trade_pnls else None,
        "profit_factor": sum(winners) / abs(sum(losers)) if losers else None,
        "sharpe_like_metric": None,
        "median_trade_pnl": sorted(trade_pnls)[len(trade_pnls) // 2] if trade_pnls else None,
        "worst_trade_pnl": min(trade_pnls) if trade_pnls else None,
        "exposure_time": None,
        "turnover": sum(_float_column(fills, "fill_notional_usd")),
        "cost_drag_bps": (sum(fee_amounts) + sum(slippage_amounts)) / initial_cash_usd * 10_000,
        "end_open_position_count": end_open_position_count,
        "end_unrealized_pnl": end_unrealized_pnl,
        "fee_impact": sum(fee_amounts),
        "funding_impact": funding_impact,
        "slippage_impact": sum(slippage_amounts),
        "taker_fill_ratio": taker_fills / fill_count if fill_count else 0.0,
        "maker_fill_ratio": 0.0,
        "blocked_reason_counts": _blocked_reason_counts(blocked_events),
        "session_breakdown": _value_counts(equity_curve, "session_type"),
        "market_status_breakdown": _value_counts(equity_curve, "market_status"),
        "source_confidence_gate_pass_rate": None,
        "venue_quality_gate_pass_rate": None,
    }
