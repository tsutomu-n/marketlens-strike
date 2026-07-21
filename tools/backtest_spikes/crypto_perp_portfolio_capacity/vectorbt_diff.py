from __future__ import annotations

from decimal import Decimal
import importlib
from typing import Any

import numpy as np
import pandas as pd

from .models import (
    PortfolioCapacityCase,
    PortfolioCapacityResult,
    VectorbtDifferentialResult,
)


TOLERANCE_USD = Decimal("0.000001")


def _decimal_sum(values: object) -> Decimal:
    return Decimal(str(float(np.asarray(values, dtype=float).sum())))


def run_vectorbt_differential(
    case: PortfolioCapacityCase,
    reference: PortfolioCapacityResult,
) -> VectorbtDifferentialResult:
    intents = reference.accepted_intents
    if not intents:
        return VectorbtDifferentialResult(
            vectorbt_version="not-run",
            reference_result_id=reference.result_id,
            reference_trade_count=0,
            vectorbt_order_count=0,
            reference_gross_pnl_usd=Decimal("0"),
            vectorbt_gross_pnl_usd=Decimal("0"),
            reference_fixed_trading_cost_usd=Decimal("0"),
            vectorbt_fixed_trading_cost_usd=Decimal("0"),
            reference_final_delta_usd=Decimal("0"),
            vectorbt_final_delta_usd=Decimal("0"),
            absolute_difference_usd=Decimal("0"),
            validated_components=[],
            unvalidated_components=[
                "no_accepted_schedule",
                "funding",
                "operator_time",
                "portfolio_scheduler",
            ],
            decision="VECTORBT_NOT_APPLICABLE",
        )
    vectorbt = importlib.import_module("vectorbt")
    index = pd.DatetimeIndex(
        sorted({intent.entry_at for intent in intents} | {intent.exit_at for intent in intents})
    )
    columns = pd.Index([intent.event_id for intent in intents])
    close = pd.DataFrame(index=index, columns=columns, dtype=float)
    size = pd.DataFrame(np.nan, index=index, columns=columns, dtype=float)
    price = pd.DataFrame(np.nan, index=index, columns=columns, dtype=float)
    fixed_fees = pd.DataFrame(0.0, index=index, columns=columns, dtype=float)
    scenario = case.policy.metric_scenario
    reference_gross = Decimal("0")
    reference_fixed_cost = Decimal("0")
    for intent in intents:
        entry_price = float(intent.entry_price_proxy)
        exit_price = float(intent.exit_price_proxy)
        close.loc[:, intent.event_id] = entry_price
        close.loc[index >= pd.Timestamp(intent.exit_at), intent.event_id] = exit_price
        quantity = float(intent.notional_usd / intent.entry_price_proxy)
        signed_quantity = quantity if intent.side == "LONG" else -quantity
        size.loc[intent.entry_at, intent.event_id] = signed_quantity
        size.loc[intent.exit_at, intent.event_id] = -signed_quantity
        price.loc[intent.entry_at, intent.event_id] = entry_price
        price.loc[intent.exit_at, intent.event_id] = exit_price
        slippage = (
            intent.slippage_estimate_usd
            if scenario == "BASE"
            else intent.stress_slippage_estimate_usd
        )
        fixed_cost = intent.fee_estimate_usd + slippage
        fixed_fees.loc[intent.entry_at, intent.event_id] = float(fixed_cost / 2)
        fixed_fees.loc[intent.exit_at, intent.event_id] = float(fixed_cost / 2)
        reference_gross += intent.before_cost_proxy_usd
        reference_fixed_cost += fixed_cost
    call_seq = np.tile(np.arange(len(columns), dtype=int), (len(index), 1))
    portfolio: Any = vectorbt.Portfolio.from_orders(
        close,
        size=size,
        size_type="amount",
        direction="both",
        price=price,
        fixed_fees=fixed_fees,
        init_cash=float(case.policy.initial_cash_usd),
        cash_sharing=True,
        group_by=True,
        call_seq=call_seq,
        allow_partial=False,
        raise_reject=True,
        lock_cash=True,
        ffill_val_price=True,
    )
    trades = portfolio.trades.records_readable
    order_count = int(len(portfolio.orders.records_readable))
    vectorbt_final = _decimal_sum(trades["PnL"])
    vectorbt_fixed = _decimal_sum(trades["Entry Fees"]) + _decimal_sum(trades["Exit Fees"])
    vectorbt_gross = vectorbt_final + vectorbt_fixed
    reference_final = reference_gross - reference_fixed_cost
    differences = (
        abs(reference_gross - vectorbt_gross),
        abs(reference_fixed_cost - vectorbt_fixed),
        abs(reference_final - vectorbt_final),
    )
    absolute_difference = max(differences)
    order_count_matches = order_count == len(intents) * 2
    decision = (
        "MATCH" if absolute_difference <= TOLERANCE_USD and order_count_matches else "MISMATCH"
    )
    return VectorbtDifferentialResult(
        vectorbt_version=str(vectorbt.__version__),
        reference_result_id=reference.result_id,
        reference_trade_count=len(intents),
        vectorbt_order_count=order_count,
        reference_gross_pnl_usd=reference_gross,
        vectorbt_gross_pnl_usd=vectorbt_gross,
        reference_fixed_trading_cost_usd=reference_fixed_cost,
        vectorbt_fixed_trading_cost_usd=vectorbt_fixed,
        reference_final_delta_usd=reference_final,
        vectorbt_final_delta_usd=vectorbt_final,
        absolute_difference_usd=absolute_difference,
        validated_components=["gross_pnl", "fixed_trading_cost", "accepted_schedule_final_delta"],
        unvalidated_components=[
            "portfolio_scheduler",
            "same_timestamp_cash_policy",
            "funding",
            "operator_time",
            "liquidation",
            "partial_fill",
        ],
        decision=decision,
    )
