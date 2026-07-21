from __future__ import annotations

from decimal import Decimal

from hypothesis import given, strategies as st

from ..models import PortfolioSkip, PortfolioTradeIntent
from ..reference_path import (
    run_reference_path,
)

from .fixtures import BASE_TIME, d
from .test_reference_path import case, intent


def _with_extra_cost(
    base: PortfolioTradeIntent,
    *,
    field_name: str,
    extra_cost: Decimal,
) -> PortfolioTradeIntent:
    return base.model_copy(
        update={
            field_name: getattr(base, field_name) + extra_cost,
            "account_delta_base_usd": base.account_delta_base_usd - extra_cost,
            "account_delta_stress_usd": base.account_delta_stress_usd - extra_cost,
            "economic_delta_base_usd": base.economic_delta_base_usd - extra_cost,
            "economic_delta_stress_usd": base.economic_delta_stress_usd - extra_cost,
            "reserve_base_usd": base.reserve_base_usd + extra_cost,
            "reserve_stress_usd": base.reserve_stress_usd + extra_cost,
        }
    )


@given(st.integers(min_value=100, max_value=1000))
def test_more_initial_cash_never_reduces_accepted_count(initial: int) -> None:
    intents = (
        intent("e1", symbol="BTCUSDT"),
        intent("e2", symbol="ETHUSDT"),
        intent("e3", symbol="SOLUSDT"),
    )
    low = run_reference_path(case(*intents, initial=str(initial)))
    high = run_reference_path(case(*intents, initial=str(initial + 100)))

    assert high.accepted_trade_count >= low.accepted_trade_count


@given(st.integers(min_value=1, max_value=3))
def test_higher_position_limit_never_reduces_accepted_count(limit: int) -> None:
    intents = (
        intent("e1", symbol="BTCUSDT"),
        intent("e2", symbol="ETHUSDT"),
        intent("e3", symbol="SOLUSDT"),
    )
    low = run_reference_path(case(*intents, maximum=limit))
    high = run_reference_path(case(*intents, maximum=limit + 1))

    assert high.accepted_trade_count >= low.accepted_trade_count


@given(st.decimals(min_value="0", max_value="5", places=2))
def test_higher_fee_never_increases_final_cash(extra_cost: Decimal) -> None:
    base = intent("e1", account_delta="5", reserve="100")
    costly = _with_extra_cost(base, field_name="fee_estimate_usd", extra_cost=extra_cost)

    assert (
        run_reference_path(case(costly)).final_available_cash_usd
        <= run_reference_path(case(base)).final_available_cash_usd
    )


@given(st.decimals(min_value="0", max_value="5", places=2))
def test_higher_slippage_never_increases_final_cash(extra_cost: Decimal) -> None:
    base = intent("e1", account_delta="5", reserve="100")
    costly = _with_extra_cost(base, field_name="slippage_estimate_usd", extra_cost=extra_cost)

    assert (
        run_reference_path(case(costly)).final_available_cash_usd
        <= run_reference_path(case(base)).final_available_cash_usd
    )


@given(st.decimals(min_value="0", max_value="5", places=2))
def test_operator_cost_never_changes_account_cash(extra_cost: Decimal) -> None:
    base = intent("e1", account_delta="5", economic_delta="5")
    costly = base.model_copy(
        update={"economic_delta_base_usd": base.economic_delta_base_usd - extra_cost}
    )
    base_result = run_reference_path(case(base))
    costly_result = run_reference_path(case(costly))

    assert costly_result.final_available_cash_usd == base_result.final_available_cash_usd
    assert costly_result.economic_result_estimate_usd <= base_result.economic_result_estimate_usd


@given(st.decimals(min_value="0", max_value="10000", places=2))
def test_no_trade_never_changes_timeline_cash(initial_cash: Decimal) -> None:
    capacity_case = case(
        initial=str(initial_cash),
        skips=(
            PortfolioSkip(
                event_id="e1",
                symbol="BTCUSDT",
                action="NO_TRADE",
                entry_at=BASE_TIME,
                reason_code="NO_TRADE_SKIPPED",
            ),
        ),
    )
    result = run_reference_path(capacity_case)

    assert result.final_available_cash_usd == initial_cash
    assert result.simulated_account_pnl_estimate_usd == 0
    for row in result.timeline:
        assert row.available_cash_before_usd == row.available_cash_after_usd
        assert row.reserved_cash_before_usd == row.reserved_cash_after_usd == 0


@given(st.integers(min_value=100, max_value=1000))
def test_run_is_deterministic(initial_cash: int) -> None:
    capacity_case = case(
        intent("e1"),
        intent("e2", symbol="ETHUSDT"),
        initial=str(initial_cash),
    )
    first = run_reference_path(capacity_case)
    second = run_reference_path(capacity_case)

    assert first.result_id == second.result_id
    assert first.timeline == second.timeline


@given(
    st.lists(
        st.decimals(min_value="1", max_value="100", places=2),
        min_size=3,
        max_size=3,
    )
)
def test_reserved_cash_matches_open_position_reserves_and_complete_run_closes_all(
    reserves: list[Decimal],
) -> None:
    intents = tuple(
        intent(
            f"e{index}",
            symbol=f"SYMBOL{index}",
            reserve=str(reserve),
            exit_minutes=60 + index,
        )
        for index, reserve in enumerate(reserves, start=1)
    )
    capacity_case = case(
        *intents,
        initial=str(sum(reserves, d("10"))),
        maximum=3,
    )
    result = run_reference_path(capacity_case)
    reserve_by_event = {value.event_id: value.reserve_base_usd for value in intents}
    open_reserves: dict[str, Decimal] = {}

    for row in result.timeline:
        if row.event_kind == "ENTRY_ACCEPTED":
            open_reserves[row.event_id] = reserve_by_event[row.event_id]
        elif row.event_kind == "EXIT_SETTLED":
            open_reserves.pop(row.event_id)
        assert row.reserved_cash_after_usd == sum(open_reserves.values(), d("0"))
        assert row.open_position_count_after == len(open_reserves)

    assert result.run_status == "COMPLETE"
    assert result.final_reserved_cash_usd == 0
    assert result.timeline[-1].open_position_count_after == 0
