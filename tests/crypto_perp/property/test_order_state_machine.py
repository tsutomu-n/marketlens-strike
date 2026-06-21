from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from sis.crypto_perp.tiny_live import OrderState, transition_order_state


@given(
    state=st.sampled_from(list(OrderState)),
    target=st.sampled_from(list(OrderState)),
)
def test_terminal_order_states_do_not_transition_to_active_states(
    state: OrderState, target: OrderState
) -> None:
    result = transition_order_state(state, target)

    if state in {OrderState.FLAT, OrderState.REJECTED, OrderState.BLOCKED_RECONCILIATION}:
        assert result == state


def test_timeout_can_only_recover_by_query_path() -> None:
    assert (
        transition_order_state(OrderState.UNKNOWN_AFTER_TIMEOUT, OrderState.ACKNOWLEDGED)
        == OrderState.ACKNOWLEDGED
    )
    assert (
        transition_order_state(OrderState.UNKNOWN_AFTER_TIMEOUT, OrderState.SUBMITTED)
        == OrderState.UNKNOWN_AFTER_TIMEOUT
    )
