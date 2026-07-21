from __future__ import annotations

import pytest

from ..vectorbt_diff import (
    run_vectorbt_differential,
)

from .test_reference_path import case, intent
from .fixtures import d
from ..reference_path import (
    run_reference_path,
)


def test_vectorbt_matches_long_short_gross_and_fixed_cost() -> None:
    pytest.importorskip("vectorbt")
    long_intent = intent("e1", account_delta="0.92").model_copy(
        update={
            "before_cost_proxy_usd": d("0.99"),
            "fee_estimate_usd": d("0.05"),
            "slippage_estimate_usd": d("0.02"),
            "reserve_base_usd": d("100.07"),
            "reserve_stress_usd": d("100.07"),
        }
    )
    short_intent = intent("e2", symbol="ETHUSDT", side="SHORT", account_delta="0.99").model_copy(
        update={
            "exit_price_proxy": d("99"),
            "before_cost_proxy_usd": d("0.99"),
            "fee_estimate_usd": d("0.05"),
            "slippage_estimate_usd": d("0.02"),
            "account_delta_base_usd": d("0.92"),
            "account_delta_stress_usd": d("0.92"),
            "economic_delta_base_usd": d("0.92"),
            "economic_delta_stress_usd": d("0.92"),
            "reserve_base_usd": d("100.07"),
            "reserve_stress_usd": d("100.07"),
        }
    )
    capacity_case = case(
        long_intent,
        short_intent,
        initial="1000",
        maximum=2,
    )
    reference = run_reference_path(capacity_case)

    result = run_vectorbt_differential(capacity_case, reference)

    assert result.decision == "MATCH"
    assert result.absolute_difference_usd <= 0.000001
    assert "gross_pnl" in result.validated_components
    assert "fixed_trading_cost" in result.validated_components
    assert result.reference_fixed_trading_cost_usd == d("0.14")
