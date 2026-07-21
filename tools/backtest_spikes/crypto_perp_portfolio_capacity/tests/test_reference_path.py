from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from typing import Literal

import pytest

from ..models import (
    PortfolioCapacityCase,
    PortfolioCapacityPolicy,
    PortfolioSkip,
    PortfolioTradeIntent,
    TimestampCashPolicy,
)
from ..reference_path import (
    run_reference_path,
)

from .fixtures import BASE_TIME, d


def intent(
    event_id: str,
    *,
    symbol: str = "BTCUSDT",
    entry_minutes: int = 0,
    exit_minutes: int = 60,
    side: Literal["LONG", "SHORT"] = "LONG",
    reserve: str = "100",
    account_delta: str = "1",
    economic_delta: str | None = None,
) -> PortfolioTradeIntent:
    action = "CONTINUATION_LONG" if side == "LONG" else "REVERSAL_SHORT"
    account = d(account_delta)
    return PortfolioTradeIntent(
        event_id=event_id,
        outcome_id=f"outcome-{event_id}",
        symbol=symbol,
        action=action,
        side=side,
        information_cutoff_at=BASE_TIME - timedelta(minutes=5),
        entry_at=BASE_TIME + timedelta(minutes=entry_minutes),
        exit_at=BASE_TIME + timedelta(minutes=exit_minutes),
        source_row_index=int(event_id.removeprefix("e") or 0),
        signal_score=Decimal("1"),
        notional_usd=d("99"),
        entry_price_proxy=d("100"),
        exit_price_proxy=d("101"),
        before_cost_proxy_usd=account,
        fee_estimate_usd=d("0"),
        funding_estimate_usd=d("0"),
        slippage_estimate_usd=d("0"),
        operator_time_cost_usd=account - d(economic_delta or account_delta),
        stress_slippage_estimate_usd=d("0"),
        account_delta_base_usd=account,
        account_delta_stress_usd=account,
        economic_delta_base_usd=d(economic_delta or account_delta),
        economic_delta_stress_usd=d(economic_delta or account_delta),
        reserve_base_usd=d(reserve),
        reserve_stress_usd=d(reserve),
        known_gaps=[],
    )


def case(
    *intents: PortfolioTradeIntent,
    initial: str = "300",
    maximum: int | None = None,
    same_timestamp: TimestampCashPolicy = "NO_SAME_TIMESTAMP_REUSE",
    skips: tuple[PortfolioSkip, ...] = (),
) -> PortfolioCapacityCase:
    policy = PortfolioCapacityPolicy(
        initial_cash_usd=d(initial),
        max_open_positions=maximum,
        action_policy="CURRENT_SELECTOR",
        metric_scenario="BASE",
        same_timestamp_cash_policy=same_timestamp,
    )
    return PortfolioCapacityCase(
        case_id="case",
        pack_id="pack",
        row_set_id="rows",
        policy=policy,
        intents=list(intents),
        skips=list(skips),
    )


@pytest.mark.parametrize(
    ("case_id", "capacity_case", "expected"),
    [
        ("G01", case(intent("e1", account_delta="5")), ("COMPLETE", 1, d("305"))),
        ("G02", case(intent("e1", account_delta="-5")), ("COMPLETE", 1, d("295"))),
        (
            "G03",
            case(intent("e1", side="SHORT", account_delta="5")),
            ("COMPLETE", 1, d("305")),
        ),
        (
            "G04",
            case(intent("e1", side="SHORT", account_delta="-5")),
            ("COMPLETE", 1, d("295")),
        ),
        (
            "G05",
            case(intent("e1"), intent("e2", symbol="ETHUSDT"), maximum=1),
            ("COMPLETE", 1, d("301")),
        ),
        (
            "G06",
            case(intent("e1"), intent("e2", symbol="ETHUSDT"), maximum=2),
            ("COMPLETE", 2, d("302")),
        ),
        ("G07", case(intent("e1"), initial="99"), ("COMPLETE", 0, d("99"))),
        (
            "G08",
            case(intent("e1"), intent("e2"), maximum=2),
            ("COMPLETE", 1, d("301")),
        ),
        (
            "G09",
            case(
                intent("e1", reserve="100", exit_minutes=60),
                intent("e2", symbol="ETHUSDT", reserve="100", entry_minutes=60, exit_minutes=120),
                initial="100",
                maximum=1,
                same_timestamp="NO_SAME_TIMESTAMP_REUSE",
            ),
            ("COMPLETE", 1, d("101")),
        ),
        (
            "G10",
            case(
                intent("e1", reserve="100", exit_minutes=60),
                intent("e2", symbol="ETHUSDT", reserve="100", entry_minutes=60, exit_minutes=120),
                initial="100",
                maximum=1,
                same_timestamp="EXIT_THEN_ENTRY",
            ),
            ("COMPLETE", 2, d("102")),
        ),
        (
            "G11",
            case(intent("e1", account_delta="5", economic_delta="2")),
            ("COMPLETE", 1, d("305")),
        ),
        (
            "G12",
            case(
                skips=(
                    PortfolioSkip(
                        event_id="e1",
                        symbol="BTCUSDT",
                        action="NO_TRADE",
                        entry_at=BASE_TIME,
                        reason_code="NO_TRADE_SKIPPED",
                    ),
                )
            ),
            ("COMPLETE", 0, d("300")),
        ),
        (
            "G13",
            case(
                skips=(
                    PortfolioSkip(
                        event_id="e1",
                        symbol="BTCUSDT",
                        action="UNKNOWN",
                        entry_at=BASE_TIME,
                        reason_code="UNKNOWN_SKIPPED",
                    ),
                )
            ),
            ("COMPLETE", 0, d("300")),
        ),
        (
            "G14",
            case(intent("e1", reserve="100", account_delta="-101"), initial="100"),
            ("INCONCLUSIVE", 1, d("0")),
        ),
    ],
)
def test_golden_reference_cases(
    case_id: str,
    capacity_case: PortfolioCapacityCase,
    expected: tuple[str, int, Decimal],
) -> None:
    result = run_reference_path(capacity_case)

    assert result.run_status == expected[0], case_id
    assert result.accepted_trade_count == expected[1], case_id
    assert result.final_available_cash_usd == expected[2], case_id


def test_g11_operator_cost_only_changes_economic_result() -> None:
    result = run_reference_path(case(intent("e1", account_delta="5", economic_delta="2")))

    assert result.simulated_account_pnl_estimate_usd == 5
    assert result.economic_result_estimate_usd == 2


def test_golden_reason_codes_and_boundaries() -> None:
    max_position = run_reference_path(case(intent("e1"), intent("e2", symbol="ETHUSDT"), maximum=1))
    insufficient_cash = run_reference_path(case(intent("e1"), initial="99"))
    duplicate_symbol = run_reference_path(case(intent("e1"), intent("e2"), maximum=2))
    no_reuse = run_reference_path(
        case(
            intent("e1", reserve="100", exit_minutes=60),
            intent("e2", symbol="ETHUSDT", reserve="100", entry_minutes=60, exit_minutes=120),
            initial="100",
            maximum=1,
            same_timestamp="NO_SAME_TIMESTAMP_REUSE",
        )
    )
    unknown = run_reference_path(
        case(
            skips=(
                PortfolioSkip(
                    event_id="e1",
                    symbol="BTCUSDT",
                    action="UNKNOWN",
                    entry_at=BASE_TIME,
                    reason_code="UNKNOWN_SKIPPED",
                ),
            )
        )
    )
    insolvency = run_reference_path(
        case(intent("e1", reserve="100", account_delta="-101"), initial="100")
    )

    assert max_position.rejected_reason_counts == {"MAX_OPEN_POSITIONS": 1}
    assert insufficient_cash.rejected_reason_counts == {"INSUFFICIENT_AVAILABLE_CASH": 1}
    assert duplicate_symbol.rejected_reason_counts == {"MAX_POSITION_PER_SYMBOL": 1}
    assert no_reuse.rejected_reason_counts == {"MAX_OPEN_POSITIONS": 1}
    assert unknown.timeline[0].event_kind == "UNKNOWN_SKIPPED"
    assert (
        unknown.timeline[0].available_cash_before_usd
        == unknown.timeline[0].available_cash_after_usd
    )
    assert insolvency.run_status == "INCONCLUSIVE"
    assert "UNMODELED_INSOLVENCY_OR_LIQUIDATION" in insolvency.known_limits
    assert insolvency.timeline[-1].reason_code == "UNMODELED_INSOLVENCY_OR_LIQUIDATION"
