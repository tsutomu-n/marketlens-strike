from __future__ import annotations

from collections import Counter
from datetime import datetime
from decimal import Decimal
from typing import Literal

from sis.crypto_perp.models import stable_hash

from .models import (
    PortfolioCapacityCase,
    PortfolioCapacityResult,
    PortfolioPosition,
    PortfolioSkip,
    PortfolioTimelineRow,
    PortfolioTradeIntent,
)

TimelineEventKind = Literal[
    "ENTRY_ACCEPTED",
    "ENTRY_REJECTED",
    "EXIT_SETTLED",
    "NO_TRADE_SKIPPED",
    "UNKNOWN_SKIPPED",
]


def _priority(intent: PortfolioTradeIntent) -> tuple[datetime, int, str]:
    return (intent.information_cutoff_at, intent.source_row_index, intent.event_id)


def run_reference_path(case: PortfolioCapacityCase) -> PortfolioCapacityResult:
    policy = case.policy
    scenario = policy.metric_scenario
    available = policy.initial_cash_usd
    reserved = Decimal("0")
    realized_account = Decimal("0")
    economic_result = Decimal("0")
    open_positions: dict[str, PortfolioPosition] = {}
    timeline: list[PortfolioTimelineRow] = []
    accepted_intents: list[PortfolioTradeIntent] = []
    rejected_reasons: Counter[str] = Counter()
    accepted_actions: Counter[str] = Counter()
    rejected_counterfactual = Decimal("0")
    peak_open = 0
    peak_reserved = Decimal("0")
    settled_peak = policy.initial_cash_usd
    max_drawdown = Decimal("0")
    run_status = "COMPLETE"
    known_limits = [
        "BAR_PROXY",
        "NO_MARK_TO_MARKET",
        "NO_LIQUIDATION_MODEL",
        "NOT_ACTUAL_CASH",
    ]

    entries_by_time: dict[datetime, list[PortfolioTradeIntent]] = {}
    exits_by_time: dict[datetime, list[PortfolioTradeIntent]] = {}
    skips_by_time: dict[datetime, list[PortfolioSkip]] = {}
    for intent in case.intents:
        entries_by_time.setdefault(intent.entry_at, []).append(intent)
        exits_by_time.setdefault(intent.exit_at, []).append(intent)
    for skip in case.skips:
        skips_by_time.setdefault(skip.entry_at, []).append(skip)
    timestamps = sorted(set(entries_by_time) | set(exits_by_time) | set(skips_by_time))

    def append_row(
        *,
        timestamp: datetime,
        event_kind: TimelineEventKind,
        event_id: str,
        symbol: str,
        action: str,
        available_before: Decimal,
        reserved_before: Decimal,
        open_before: int,
        account_delta: Decimal = Decimal("0"),
        economic_delta: Decimal = Decimal("0"),
        reason_code: str | None = None,
    ) -> None:
        timeline.append(
            PortfolioTimelineRow(
                timestamp=timestamp,
                event_kind=event_kind,
                event_id=event_id,
                symbol=symbol,
                action=action,
                available_cash_before_usd=available_before,
                available_cash_after_usd=available,
                reserved_cash_before_usd=reserved_before,
                reserved_cash_after_usd=reserved,
                open_position_count_before=open_before,
                open_position_count_after=len(open_positions),
                account_delta_usd=account_delta,
                economic_delta_usd=economic_delta,
                reason_code=reason_code,
            )
        )

    def process_entries(timestamp: datetime) -> None:
        nonlocal available, reserved, peak_open, peak_reserved, rejected_counterfactual
        for intent in sorted(entries_by_time.get(timestamp, []), key=_priority):
            available_before = available
            reserved_before = reserved
            open_before = len(open_positions)
            reserve_amount = intent.reserve(scenario)
            reason: str | None = None
            if intent.event_id in open_positions:
                reason = "DUPLICATE_EVENT_POSITION"
            elif (
                sum(position.symbol == intent.symbol for position in open_positions.values())
                >= policy.max_open_positions_per_symbol
            ):
                reason = "MAX_POSITION_PER_SYMBOL"
            elif (
                policy.max_open_positions is not None
                and len(open_positions) >= policy.max_open_positions
            ):
                reason = "MAX_OPEN_POSITIONS"
            elif available < reserve_amount:
                reason = "INSUFFICIENT_AVAILABLE_CASH"
            if reason is not None:
                rejected_reasons[reason] += 1
                rejected_counterfactual += intent.account_delta(scenario)
                append_row(
                    timestamp=timestamp,
                    event_kind="ENTRY_REJECTED",
                    event_id=intent.event_id,
                    symbol=intent.symbol,
                    action=intent.action,
                    available_before=available_before,
                    reserved_before=reserved_before,
                    open_before=open_before,
                    reason_code=reason,
                )
                continue
            available -= reserve_amount
            reserved += reserve_amount
            open_positions[intent.event_id] = PortfolioPosition(
                event_id=intent.event_id,
                symbol=intent.symbol,
                action=intent.action,
                entry_at=intent.entry_at,
                exit_at=intent.exit_at,
                reserve_usd=reserve_amount,
                account_delta_usd=intent.account_delta(scenario),
                economic_delta_usd=intent.economic_delta(scenario),
                intent=intent,
            )
            accepted_intents.append(intent)
            accepted_actions[intent.action] += 1
            peak_open = max(peak_open, len(open_positions))
            peak_reserved = max(peak_reserved, reserved)
            append_row(
                timestamp=timestamp,
                event_kind="ENTRY_ACCEPTED",
                event_id=intent.event_id,
                symbol=intent.symbol,
                action=intent.action,
                available_before=available_before,
                reserved_before=reserved_before,
                open_before=open_before,
            )

    def process_skips(timestamp: datetime) -> None:
        for skip in sorted(skips_by_time.get(timestamp, []), key=lambda value: value.event_id):
            append_row(
                timestamp=timestamp,
                event_kind=skip.reason_code,
                event_id=skip.event_id,
                symbol=skip.symbol,
                action=skip.action,
                available_before=available,
                reserved_before=reserved,
                open_before=len(open_positions),
                reason_code=skip.reason_code,
            )

    def process_exits(timestamp: datetime) -> bool:
        nonlocal available, reserved, realized_account, economic_result
        nonlocal settled_peak, max_drawdown, run_status
        for intent in sorted(exits_by_time.get(timestamp, []), key=lambda value: value.event_id):
            position = open_positions.get(intent.event_id)
            if position is None:
                continue
            available_before = available
            reserved_before = reserved
            open_before = len(open_positions)
            if position.reserve_usd + position.account_delta_usd < 0:
                run_status = "INCONCLUSIVE"
                known_limits.append("UNMODELED_INSOLVENCY_OR_LIQUIDATION")
                append_row(
                    timestamp=timestamp,
                    event_kind="EXIT_SETTLED",
                    event_id=intent.event_id,
                    symbol=intent.symbol,
                    action=intent.action,
                    available_before=available_before,
                    reserved_before=reserved_before,
                    open_before=open_before,
                    reason_code="UNMODELED_INSOLVENCY_OR_LIQUIDATION",
                )
                return False
            open_positions.pop(intent.event_id)
            reserved -= position.reserve_usd
            available += position.reserve_usd + position.account_delta_usd
            realized_account += position.account_delta_usd
            economic_result += position.economic_delta_usd
            settled_balance = policy.initial_cash_usd + realized_account
            settled_peak = max(settled_peak, settled_balance)
            max_drawdown = min(max_drawdown, settled_balance - settled_peak)
            append_row(
                timestamp=timestamp,
                event_kind="EXIT_SETTLED",
                event_id=intent.event_id,
                symbol=intent.symbol,
                action=intent.action,
                available_before=available_before,
                reserved_before=reserved_before,
                open_before=open_before,
                account_delta=position.account_delta_usd,
                economic_delta=position.economic_delta_usd,
            )
        return True

    for timestamp in timestamps:
        if policy.same_timestamp_cash_policy == "EXIT_THEN_ENTRY":
            if not process_exits(timestamp):
                break
            process_entries(timestamp)
            process_skips(timestamp)
        else:
            process_entries(timestamp)
            process_skips(timestamp)
            if not process_exits(timestamp):
                break
        if available < 0 or reserved < 0:
            raise AssertionError("negative cash state")
        if reserved != sum(position.reserve_usd for position in open_positions.values()):
            raise AssertionError("reserved cash does not match open positions")

    if run_status == "COMPLETE" and open_positions:
        raise AssertionError("complete run ended with open positions")
    if run_status == "COMPLETE" and reserved != 0:
        raise AssertionError("complete run ended with reserved cash")
    result_payload = {
        "case_id": case.case_id,
        "pack_id": case.pack_id,
        "row_set_id": case.row_set_id,
        "policy": policy.model_dump(mode="json"),
        "timeline": [row.model_dump(mode="json") for row in timeline],
        "run_status": run_status,
    }
    utilization = (
        peak_reserved / policy.initial_cash_usd if policy.initial_cash_usd > 0 else Decimal("0")
    )
    return PortfolioCapacityResult(
        result_id=stable_hash(["crypto-perp-portfolio-capacity", result_payload]),
        case_id=case.case_id,
        pack_id=case.pack_id,
        row_set_id=case.row_set_id,
        metric_scenario=scenario,
        same_timestamp_cash_policy=policy.same_timestamp_cash_policy,
        initial_cash_usd=policy.initial_cash_usd,
        final_available_cash_usd=available,
        final_reserved_cash_usd=reserved,
        simulated_account_pnl_estimate_usd=realized_account,
        economic_result_estimate_usd=economic_result,
        accepted_trade_count=len(accepted_intents),
        rejected_trade_count=sum(rejected_reasons.values()),
        skipped_trade_count=len(case.skips),
        peak_open_positions=peak_open,
        peak_reserved_cash_usd=peak_reserved,
        peak_capital_utilization=utilization,
        settled_cash_drawdown_estimate_usd=max_drawdown,
        accepted_action_counts=dict(sorted(accepted_actions.items())),
        rejected_reason_counts=dict(sorted(rejected_reasons.items())),
        rejected_counterfactual_estimate_usd=rejected_counterfactual,
        run_status=run_status,
        known_limits=list(dict.fromkeys(known_limits)),
        timeline=timeline,
        accepted_intents=accepted_intents,
    )
