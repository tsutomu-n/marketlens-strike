from __future__ import annotations

from decimal import Decimal

from hypothesis import given
from hypothesis import strategies as st

from sis.crypto_perp.order_preview import round_down_to_step


@given(
    value=st.decimals(
        min_value=Decimal("0.001"),
        max_value=Decimal("100000"),
        allow_nan=False,
        allow_infinity=False,
        places=6,
    ),
    step=st.sampled_from([Decimal("0.001"), Decimal("0.01"), Decimal("0.1"), Decimal("1")]),
)
def test_round_down_to_step_never_exceeds_input_and_is_step_multiple(
    value: Decimal, step: Decimal
) -> None:
    rounded = round_down_to_step(value, step)

    assert rounded <= value
    assert rounded >= 0
    assert rounded / step == (rounded / step).to_integral_value()
