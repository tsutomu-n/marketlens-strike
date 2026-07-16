from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from sis.crypto_perp.clock import ensure_utc_aware
from sis.crypto_perp.models import CryptoPerpProducer, stable_hash
from sis.crypto_perp.portfolio_capacity.models import (
    PortfolioCapacityCase,
    PortfolioCapacityResult,
    PortfolioTradeIntent,
    VectorbtDifferentialResult,
)


def _accepted_event_ids(result: PortfolioCapacityResult) -> list[str]:
    return [
        row.event_id
        for row in result.timeline
        if row.event_kind == "ENTRY_ACCEPTED"
    ]


def _gross_and_fixed_cost(intent: PortfolioTradeIntent, scenario: str) -> Decimal:
    slippage = (
        intent.slippage_estimate_usd
        if scenario == "BASE"
        else intent.stress_slippage_estimate_usd
    )
    return intent.before_cost_proxy_usd - intent.fee_estimate_usd - slippage


def _sum_decimal(value: Any) -> Decimal:
    if hasattr(value, "sum"):
        try:
            value = value.sum()
        except Exception:
            pass
    if hasattr(value, "item"):
        try:
            value = value.item()
        except Exception:
            pass
    return Decimal(str(value))


def _vectorbt_version(module: Any) -> str | None:
    value = getattr(module, "__version__", None)
    return str(value) if value is not None else None


def run_vectorbt_differential(
    case: PortfolioCapacityCase,
    reference: PortfolioCapacityResult,
    *,
    created_at: datetime | str,
    vectorbt_module: Any | None = None,
    tolerance_usd: Decimal = Decimal("0.000001"),
) -> VectorbtDifferentialResult:
    created = ensure_utc_aware("created_at", created_at)
    if vectorbt_module is None:
        try:
            import vectorbt as vectorbt_module  # type: ignore[import-not-found,no-redef]
        except ImportError:
            return VectorbtDifferentialResult(
                artifact_id=stable_hash(["vectorbt-diff", case.case_id, "not-available"]),
                created_at=created,
                producer=CryptoPerpProducer(command="crypto-perp-portfolio-capacity"),
                source_refs=list(case.source_refs),
                case_id=case.case_id,
                reference_result_id=reference.result_id,
                vectorbt_version=None,
                run_status="SKIPPED",
                decision="VECTORBT_NOT_AVAILABLE",
                reference_trade_count=reference.accepted_trade_count,
                vectorbt_order_count=None,
                reference_gross_and_fixed_cost_usd=Decimal("0"),
                vectorbt_total_profit_usd=None,
                absolute_difference_usd=None,
                tolerance_usd=tolerance_usd,
                validated_components=[],
                unvalidated_components=[
                    "portfolio_scheduler",
                    "funding",
                    "operator_time",
                    "liquidation",
                    "partial_fill",
                ],
                reason_codes=["VECTORBT_OPTIONAL_EXTRA_NOT_INSTALLED"],
            )

    accepted_ids = _accepted_event_ids(reference)
    intent_by_event = {intent.event_id: intent for intent in case.intents}
    accepted = [intent_by_event[event_id] for event_id in accepted_ids]
    expected = sum(
        (
            _gross_and_fixed_cost(intent, case.policy.metric_scenario)
            for intent in accepted
        ),
        Decimal("0"),
    )
    if not accepted:
        return VectorbtDifferentialResult(
            artifact_id=stable_hash(["vectorbt-diff", case.case_id, "no-trades"]),
            created_at=created,
            producer=CryptoPerpProducer(command="crypto-perp-portfolio-capacity"),
            source_refs=list(case.source_refs),
            case_id=case.case_id,
            reference_result_id=reference.result_id,
            vectorbt_version=_vectorbt_version(vectorbt_module),
            run_status="COMPLETED",
            decision="MATCH",
            reference_trade_count=0,
            vectorbt_order_count=0,
            reference_gross_and_fixed_cost_usd=Decimal("0"),
            vectorbt_total_profit_usd=Decimal("0"),
            absolute_difference_usd=Decimal("0"),
            tolerance_usd=tolerance_usd,
            validated_components=["no_trade_schedule"],
            unvalidated_components=[
                "portfolio_scheduler",
                "shared_cash_accounting",
                "funding",
                "operator_time",
                "liquidation",
                "partial_fill",
            ],
            reason_codes=[],
        )

    try:
        import numpy as np
        import pandas as pd

        ordered = sorted(
            accepted,
            key=lambda item: (item.entry_at, item.source_row_index, item.event_id),
        )
        timestamps = sorted(
            {item.entry_at for item in ordered} | {item.exit_at for item in ordered}
        )
        columns = [item.event_id for item in ordered]
        index_by_time = {value: index for index, value in enumerate(timestamps)}
        close = np.ones((len(timestamps), len(columns)), dtype=float)
        size = np.full((len(timestamps), len(columns)), np.nan, dtype=float)
        price = np.full((len(timestamps), len(columns)), np.nan, dtype=float)
        fixed_fees = np.zeros((len(timestamps), len(columns)), dtype=float)
        for column_index, intent in enumerate(ordered):
            gross_return = intent.before_cost_proxy_usd / intent.notional_usd
            exit_price = (
                Decimal("1") + gross_return
                if intent.side == "LONG"
                else Decimal("1") - gross_return
            )
            if exit_price <= 0:
                raise ValueError(
                    f"VECTORBT_SYNTHETIC_EXIT_PRICE_NON_POSITIVE: {intent.event_id}"
                )
            entry_index = index_by_time[intent.entry_at]
            exit_index = index_by_time[intent.exit_at]
            close[exit_index:, column_index] = float(exit_price)
            quantity = float(intent.notional_usd)
            size[entry_index, column_index] = (
                quantity if intent.side == "LONG" else -quantity
            )
            size[exit_index, column_index] = (
                -quantity if intent.side == "LONG" else quantity
            )
            price[entry_index, column_index] = 1.0
            price[exit_index, column_index] = float(exit_price)
            slippage = (
                intent.slippage_estimate_usd
                if case.policy.metric_scenario == "BASE"
                else intent.stress_slippage_estimate_usd
            )
            per_leg_fixed = float(
                (intent.fee_estimate_usd + slippage) / Decimal("2")
            )
            fixed_fees[entry_index, column_index] = per_leg_fixed
            fixed_fees[exit_index, column_index] = per_leg_fixed

        close_frame = pd.DataFrame(close, index=timestamps, columns=columns)
        size_frame = pd.DataFrame(size, index=timestamps, columns=columns)
        price_frame = pd.DataFrame(price, index=timestamps, columns=columns)
        fixed_fee_frame = pd.DataFrame(fixed_fees, index=timestamps, columns=columns)
        portfolio = vectorbt_module.Portfolio.from_orders(
            close_frame,
            size=size_frame,
            price=price_frame,
            size_type="amount",
            direction="both",
            fees=0.0,
            fixed_fees=fixed_fee_frame,
            slippage=0.0,
            init_cash=float(case.policy.initial_cash_usd),
            cash_sharing=False,
            group_by=False,
        )
        total_profit = _sum_decimal(portfolio.total_profit())
        try:
            order_count = int(_sum_decimal(portfolio.orders.count()))
        except Exception:
            order_count = len(ordered) * 2
        difference = abs(total_profit - expected)
        decision = "MATCH" if difference <= tolerance_usd else "MISMATCH"
        reason_codes = (
            [] if decision == "MATCH" else ["VECTORBT_REFERENCE_RESULT_MISMATCH"]
        )
        return VectorbtDifferentialResult(
            artifact_id=stable_hash(
                ["vectorbt-diff", case.case_id, str(total_profit), str(expected), decision]
            ),
            created_at=created,
            producer=CryptoPerpProducer(command="crypto-perp-portfolio-capacity"),
            source_refs=list(case.source_refs),
            case_id=case.case_id,
            reference_result_id=reference.result_id,
            vectorbt_version=_vectorbt_version(vectorbt_module),
            run_status="COMPLETED",
            decision=decision,
            reference_trade_count=len(ordered),
            vectorbt_order_count=order_count,
            reference_gross_and_fixed_cost_usd=expected,
            vectorbt_total_profit_usd=total_profit,
            absolute_difference_usd=difference,
            tolerance_usd=tolerance_usd,
            validated_components=["gross_pnl", "fee_estimate", "slippage_estimate"],
            unvalidated_components=[
                "portfolio_scheduler",
                "shared_cash_accounting",
                "funding",
                "operator_time",
                "liquidation",
                "partial_fill",
                "market_price_path",
            ],
            reason_codes=reason_codes,
        )
    except Exception as exc:
        return VectorbtDifferentialResult(
            artifact_id=stable_hash(["vectorbt-diff", case.case_id, "failed", str(exc)]),
            created_at=created,
            producer=CryptoPerpProducer(command="crypto-perp-portfolio-capacity"),
            source_refs=list(case.source_refs),
            case_id=case.case_id,
            reference_result_id=reference.result_id,
            vectorbt_version=_vectorbt_version(vectorbt_module),
            run_status="FAILED",
            decision="VECTORBT_NOT_APPLICABLE",
            reference_trade_count=len(accepted),
            vectorbt_order_count=None,
            reference_gross_and_fixed_cost_usd=expected,
            vectorbt_total_profit_usd=None,
            absolute_difference_usd=None,
            tolerance_usd=tolerance_usd,
            validated_components=[],
            unvalidated_components=[
                "portfolio_scheduler",
                "shared_cash_accounting",
                "funding",
                "operator_time",
                "liquidation",
                "partial_fill",
            ],
            reason_codes=[f"VECTORBT_RUN_FAILED:{type(exc).__name__}:{exc}"],
        )
