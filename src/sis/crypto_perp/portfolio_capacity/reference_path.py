from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Literal, cast

from sis.crypto_perp.clock import ensure_utc_aware
from sis.crypto_perp.models import CryptoPerpProducer, stable_hash
from sis.crypto_perp.portfolio_capacity.models import (
    PortfolioCapacityCase,
    PortfolioCapacityResult,
    PortfolioSkippedSignal,
    PortfolioTimelineRow,
    PortfolioTradeIntent,
    TimelineEventKind,
)


@dataclass(frozen=True)
class _OpenPosition:
    intent: PortfolioTradeIntent
    reserve_usd: Decimal
    account_delta_usd: Decimal
    economic_delta_usd: Decimal


@dataclass
class _State:
    available_cash_usd: Decimal
    reserved_cash_usd: Decimal
    open_positions: dict[str, _OpenPosition]


def _scenario_values(
    intent: PortfolioTradeIntent,
    scenario: Literal["BASE", "STRESS"],
) -> tuple[Decimal, Decimal, Decimal]:
    if scenario == "BASE":
        return (
            intent.reserve_base_usd,
            intent.account_delta_base_usd,
            intent.economic_delta_base_usd,
        )
    return (
        intent.reserve_stress_usd,
        intent.account_delta_stress_usd,
        intent.economic_delta_stress_usd,
    )


def _state_snapshot(state: _State) -> tuple[Decimal, Decimal, int]:
    return state.available_cash_usd, state.reserved_cash_usd, len(state.open_positions)


def _timeline_row(
    *,
    timestamp: datetime,
    event_kind: str,
    event_id: str,
    symbol: str,
    action: str,
    before: tuple[Decimal, Decimal, int],
    after: tuple[Decimal, Decimal, int],
    account_delta_usd: Decimal = Decimal("0"),
    economic_delta_usd: Decimal = Decimal("0"),
    reason_code: str | None = None,
) -> PortfolioTimelineRow:
    return PortfolioTimelineRow(
        timestamp=timestamp,
        event_kind=cast(TimelineEventKind, event_kind),
        event_id=event_id,
        symbol=symbol,
        action=action,
        available_cash_before_usd=before[0],
        available_cash_after_usd=after[0],
        reserved_cash_before_usd=before[1],
        reserved_cash_after_usd=after[1],
        open_position_count_before=before[2],
        open_position_count_after=after[2],
        account_delta_usd=account_delta_usd,
        economic_delta_usd=economic_delta_usd,
        reason_code=reason_code,
    )


def _entry_rejection_reason(
    state: _State,
    *,
    intent: PortfolioTradeIntent,
    reserve_usd: Decimal,
    max_open_positions: int | None,
    max_open_positions_per_symbol: int,
) -> str | None:
    if intent.event_id in state.open_positions:
        return "DUPLICATE_EVENT_POSITION"
    same_symbol_count = sum(
        position.intent.symbol == intent.symbol for position in state.open_positions.values()
    )
    if same_symbol_count >= max_open_positions_per_symbol:
        return "MAX_POSITION_PER_SYMBOL"
    if max_open_positions is not None and len(state.open_positions) >= max_open_positions:
        return "MAX_OPEN_POSITIONS"
    if state.available_cash_usd < reserve_usd:
        return "INSUFFICIENT_AVAILABLE_CASH"
    return None


def _apply_entry(
    state: _State,
    *,
    intent: PortfolioTradeIntent,
    reserve_usd: Decimal,
    account_delta_usd: Decimal,
    economic_delta_usd: Decimal,
) -> None:
    state.available_cash_usd -= reserve_usd
    state.reserved_cash_usd += reserve_usd
    state.open_positions[intent.event_id] = _OpenPosition(
        intent=intent,
        reserve_usd=reserve_usd,
        account_delta_usd=account_delta_usd,
        economic_delta_usd=economic_delta_usd,
    )


def _check_state(state: _State) -> None:
    if state.available_cash_usd < 0:
        raise AssertionError("available cash must be non-negative")
    if state.reserved_cash_usd < 0:
        raise AssertionError("reserved cash must be non-negative")
    expected_reserved = sum(
        (position.reserve_usd for position in state.open_positions.values()), Decimal("0")
    )
    if expected_reserved != state.reserved_cash_usd:
        raise AssertionError("reserved cash must match open position reserves")


def _record_entry(
    state: _State,
    *,
    intent: PortfolioTradeIntent,
    scenario: Literal["BASE", "STRESS"],
    max_open_positions: int | None,
    max_open_positions_per_symbol: int,
    timeline: list[PortfolioTimelineRow],
    rejected_reasons: Counter[str],
    rejected_counterfactual: list[Decimal],
) -> bool:
    reserve, account_delta, economic_delta = _scenario_values(intent, scenario)
    before = _state_snapshot(state)
    reason = _entry_rejection_reason(
        state,
        intent=intent,
        reserve_usd=reserve,
        max_open_positions=max_open_positions,
        max_open_positions_per_symbol=max_open_positions_per_symbol,
    )
    if reason is not None:
        rejected_reasons[reason] += 1
        rejected_counterfactual.append(economic_delta)
        timeline.append(
            _timeline_row(
                timestamp=intent.entry_at,
                event_kind="ENTRY_REJECTED",
                event_id=intent.event_id,
                symbol=intent.symbol,
                action=intent.action,
                before=before,
                after=before,
                reason_code=reason,
            )
        )
        return False
    _apply_entry(
        state,
        intent=intent,
        reserve_usd=reserve,
        account_delta_usd=account_delta,
        economic_delta_usd=economic_delta,
    )
    after = _state_snapshot(state)
    timeline.append(
        _timeline_row(
            timestamp=intent.entry_at,
            event_kind="ENTRY_ACCEPTED",
            event_id=intent.event_id,
            symbol=intent.symbol,
            action=intent.action,
            before=before,
            after=after,
        )
    )
    _check_state(state)
    return True


def _record_exit(
    state: _State,
    *,
    intent: PortfolioTradeIntent,
    timeline: list[PortfolioTimelineRow],
) -> tuple[bool, Decimal, Decimal]:
    position = state.open_positions.get(intent.event_id)
    if position is None:
        return True, Decimal("0"), Decimal("0")
    before = _state_snapshot(state)
    if position.reserve_usd + position.account_delta_usd < 0:
        timeline.append(
            _timeline_row(
                timestamp=intent.exit_at,
                event_kind="EXIT_BLOCKED",
                event_id=intent.event_id,
                symbol=intent.symbol,
                action=intent.action,
                before=before,
                after=before,
                reason_code="UNMODELED_INSOLVENCY_OR_LIQUIDATION",
            )
        )
        return False, Decimal("0"), Decimal("0")
    del state.open_positions[intent.event_id]
    state.reserved_cash_usd -= position.reserve_usd
    state.available_cash_usd += position.reserve_usd + position.account_delta_usd
    after = _state_snapshot(state)
    timeline.append(
        _timeline_row(
            timestamp=intent.exit_at,
            event_kind="EXIT_SETTLED",
            event_id=intent.event_id,
            symbol=intent.symbol,
            action=intent.action,
            before=before,
            after=after,
            account_delta_usd=position.account_delta_usd,
            economic_delta_usd=position.economic_delta_usd,
        )
    )
    _check_state(state)
    return True, position.account_delta_usd, position.economic_delta_usd


def _entry_sort_key(intent: PortfolioTradeIntent) -> tuple[datetime, int, str]:
    return intent.information_cutoff_at, intent.source_row_index, intent.event_id


def _drawdown(values: list[Decimal]) -> Decimal:
    peak = values[0] if values else Decimal("0")
    worst = Decimal("0")
    for value in values:
        peak = max(peak, value)
        worst = min(worst, value - peak)
    return worst


def run_reference_portfolio_path(
    case: PortfolioCapacityCase,
    *,
    created_at: datetime | str,
) -> PortfolioCapacityResult:
    created = ensure_utc_aware("created_at", created_at)
    state = _State(
        available_cash_usd=case.policy.initial_cash_usd,
        reserved_cash_usd=Decimal("0"),
        open_positions={},
    )
    timeline: list[PortfolioTimelineRow] = []
    accepted_actions: Counter[str] = Counter()
    rejected_reasons: Counter[str] = Counter()
    rejected_counterfactual: list[Decimal] = []
    account_result = Decimal("0")
    economic_result = Decimal("0")
    settled_values = [case.policy.initial_cash_usd]
    run_status: Literal["COMPLETE", "INCONCLUSIVE", "INVALID_INPUT"] = "COMPLETE"
    known_limits = list(case.known_limits)

    entries_by_ts: dict[datetime, list[PortfolioTradeIntent]] = defaultdict(list)
    exits_by_ts: dict[datetime, list[PortfolioTradeIntent]] = defaultdict(list)
    skips_by_ts: dict[datetime, list[PortfolioSkippedSignal]] = defaultdict(list)
    for intent in case.intents:
        entries_by_ts[intent.entry_at].append(intent)
        exits_by_ts[intent.exit_at].append(intent)
    for skipped in case.skipped_signals:
        skips_by_ts[skipped.information_cutoff_at].append(skipped)
    timestamps = sorted(set(entries_by_ts) | set(exits_by_ts) | set(skips_by_ts))

    for timestamp in timestamps:
        for skipped in sorted(
            skips_by_ts.get(timestamp, []),
            key=lambda item: (item.source_row_index, item.event_id),
        ):
            snapshot = _state_snapshot(state)
            timeline.append(
                _timeline_row(
                    timestamp=timestamp,
                    event_kind=(
                        "NO_TRADE_SKIPPED"
                        if skipped.selected_action == "NO_TRADE"
                        else "UNKNOWN_SKIPPED"
                    ),
                    event_id=skipped.event_id,
                    symbol=skipped.symbol,
                    action=skipped.selected_action,
                    before=snapshot,
                    after=snapshot,
                )
            )

        entries = sorted(entries_by_ts.get(timestamp, []), key=_entry_sort_key)
        exits = sorted(exits_by_ts.get(timestamp, []), key=lambda item: item.event_id)
        if case.policy.same_timestamp_cash_policy == "NO_SAME_TIMESTAMP_REUSE":
            for intent in entries:
                if _record_entry(
                    state,
                    intent=intent,
                    scenario=case.policy.metric_scenario,
                    max_open_positions=case.policy.max_open_positions,
                    max_open_positions_per_symbol=case.policy.max_open_positions_per_symbol,
                    timeline=timeline,
                    rejected_reasons=rejected_reasons,
                    rejected_counterfactual=rejected_counterfactual,
                ):
                    accepted_actions[intent.action] += 1
            for intent in exits:
                ok, account_delta, economic_delta = _record_exit(
                    state,
                    intent=intent,
                    timeline=timeline,
                )
                if not ok:
                    run_status = "INCONCLUSIVE"
                    known_limits.append("UNMODELED_INSOLVENCY_OR_LIQUIDATION")
                    break
                account_result += account_delta
                economic_result += economic_delta
                settled_values.append(state.available_cash_usd + state.reserved_cash_usd)
        else:
            for intent in exits:
                ok, account_delta, economic_delta = _record_exit(
                    state,
                    intent=intent,
                    timeline=timeline,
                )
                if not ok:
                    run_status = "INCONCLUSIVE"
                    known_limits.append("UNMODELED_INSOLVENCY_OR_LIQUIDATION")
                    break
                account_result += account_delta
                economic_result += economic_delta
                settled_values.append(state.available_cash_usd + state.reserved_cash_usd)
            if run_status == "COMPLETE":
                for intent in entries:
                    if _record_entry(
                        state,
                        intent=intent,
                        scenario=case.policy.metric_scenario,
                        max_open_positions=case.policy.max_open_positions,
                        max_open_positions_per_symbol=case.policy.max_open_positions_per_symbol,
                        timeline=timeline,
                        rejected_reasons=rejected_reasons,
                        rejected_counterfactual=rejected_counterfactual,
                    ):
                        accepted_actions[intent.action] += 1
        if run_status != "COMPLETE":
            break

    if run_status == "COMPLETE" and (state.open_positions or state.reserved_cash_usd != 0):
        run_status = "INVALID_INPUT"
        known_limits.append("OPEN_POSITION_REMAINS_AFTER_FINAL_EVENT")

    final_available = state.available_cash_usd
    if run_status == "COMPLETE":
        expected_final = case.policy.initial_cash_usd + account_result
        if final_available != expected_final:
            raise AssertionError("final available cash must equal initial cash plus settled account PnL")
    peak_open_positions = max((row.open_position_count_after for row in timeline), default=0)
    peak_reserved = max(
        (row.reserved_cash_after_usd for row in timeline),
        default=Decimal("0"),
    )
    result_id = stable_hash(
        [
            "crypto-perp-portfolio-capacity-result",
            case.case_id,
            run_status,
            final_available,
            state.reserved_cash_usd,
            [row.model_dump(mode="json") for row in timeline],
        ]
    )
    return PortfolioCapacityResult(
        result_id=result_id,
        created_at=created,
        producer=CryptoPerpProducer(command="crypto-perp-portfolio-capacity"),
        source_refs=list(case.source_refs),
        case_id=case.case_id,
        pack_id=case.pack_id,
        row_set_id=case.row_set_id,
        metric_scenario=case.policy.metric_scenario,
        same_timestamp_cash_policy=case.policy.same_timestamp_cash_policy,
        initial_cash_usd=case.policy.initial_cash_usd,
        final_available_cash_usd=final_available,
        final_reserved_cash_usd=state.reserved_cash_usd,
        simulated_account_pnl_estimate_usd=account_result,
        economic_result_estimate_usd=economic_result,
        accepted_trade_count=sum(accepted_actions.values()),
        rejected_trade_count=sum(rejected_reasons.values()),
        skipped_trade_count=len(case.skipped_signals),
        peak_open_positions=peak_open_positions,
        peak_reserved_cash_usd=peak_reserved,
        peak_capital_utilization=(
            peak_reserved / case.policy.initial_cash_usd
            if case.policy.initial_cash_usd > 0
            else Decimal("0")
        ),
        settled_cash_drawdown_estimate_usd=_drawdown(settled_values),
        accepted_action_counts=dict(sorted(accepted_actions.items())),
        rejected_reason_counts=dict(sorted(rejected_reasons.items())),
        rejected_counterfactual_estimate_usd=sum(rejected_counterfactual, Decimal("0")),
        run_status=run_status,
        known_limits=list(dict.fromkeys(known_limits)),
        timeline=timeline,
    )
