from __future__ import annotations

import pytest

from sis.research.strategy_lab.authoring.backtest_bundle_metrics import (
    _aggregate_bundle_metrics,
    _bundle_effective_weights,
)
from sis.research.strategy_lab.authoring.contracts.spec import StrategyAuthoringBundleSpec


def _bundle(
    allocation_method: str, *, max_total: float | None = None
) -> StrategyAuthoringBundleSpec:
    payload = {
        "schema_version": "strategy_authoring_bundle.v1",
        "bundle_id": "bundle_metrics_test",
        "members": [
            {"spec_path": "first.yaml", "allocation_weight": 0.7},
            {"spec_path": "second.yaml", "allocation_weight": 0.5},
        ],
        "portfolio": {"allocation_method": allocation_method},
    }
    if max_total is not None:
        payload["portfolio"]["max_total_allocation_weight"] = max_total
    return StrategyAuthoringBundleSpec.model_validate(payload)


def _member(
    index: int,
    *,
    weight: float,
    total_return: float,
    max_drawdown: float | None,
    group_metrics: dict[str, float | int | None],
) -> dict[str, object]:
    return {
        "member_index": index,
        "effective_allocation_weight": weight,
        "summary": {
            "aggregate_metrics": {
                "trade_count": 2 + index,
                "total_return": total_return,
                "max_drawdown": max_drawdown,
                "cost_drag_bps": 1.0 + index,
            },
            "multi_leg_group_metrics": group_metrics,
        },
    }


def test_bundle_effective_weights_scale_fixed_weights_to_total_cap() -> None:
    weights = _bundle_effective_weights(
        _bundle("fixed_weight", max_total=1.0),
        [
            _member(0, weight=0.0, total_return=0.0, max_drawdown=-0.1, group_metrics={}),
            _member(1, weight=0.0, total_return=0.0, max_drawdown=-0.2, group_metrics={}),
        ],
    )

    assert weights == pytest.approx({0: 0.5833333333, 1: 0.4166666667})


def test_bundle_effective_weights_use_inverse_drawdown_for_risk_parity() -> None:
    weights = _bundle_effective_weights(
        _bundle("risk_parity"),
        [
            _member(0, weight=0.0, total_return=0.0, max_drawdown=-0.1, group_metrics={}),
            _member(1, weight=0.0, total_return=0.0, max_drawdown=-0.2, group_metrics={}),
        ],
    )

    assert weights == pytest.approx({0: 0.6666666667, 1: 0.3333333333})


def test_aggregate_bundle_metrics_weights_member_and_multi_leg_group_metrics() -> None:
    first_group = {
        "group_count": 1,
        "executed_group_count": 1,
        "complete_group_count": 1,
        "incomplete_group_count": 0,
        "expected_leg_count": 2,
        "executed_leg_count": 2,
        "total_return": 0.04,
        "avg_group_return": 0.04,
        "win_rate": 1.0,
        "worst_group_return": 0.04,
        "max_drawdown": -0.01,
        "profit_factor": 2.0,
        "avg_leg_return_imbalance": 0.002,
        "total_notional_usd": 1000.0,
        "notional_weighted_total_return": 0.03,
        "cost_drag_bps": 1.0,
    }
    second_group = {
        "group_count": 2,
        "executed_group_count": 1,
        "complete_group_count": 1,
        "incomplete_group_count": 1,
        "expected_leg_count": 4,
        "executed_leg_count": 3,
        "total_return": -0.02,
        "avg_group_return": -0.02,
        "win_rate": 0.0,
        "worst_group_return": -0.02,
        "max_drawdown": -0.03,
        "profit_factor": None,
        "avg_leg_return_imbalance": 0.006,
        "total_notional_usd": 500.0,
        "notional_weighted_total_return": -0.01,
        "cost_drag_bps": 2.0,
    }
    members = [
        _member(0, weight=0.6, total_return=0.10, max_drawdown=-0.2, group_metrics=first_group),
        _member(1, weight=0.4, total_return=-0.05, max_drawdown=-0.1, group_metrics=second_group),
    ]

    aggregate = _aggregate_bundle_metrics(members)
    group_aggregate = aggregate["multi_leg_group_metrics"]

    assert aggregate["member_count"] == 2
    assert aggregate["trade_count"] == 5
    assert aggregate["weighted_total_return"] == pytest.approx(0.04)
    assert aggregate["max_drawdown"] == pytest.approx(-0.12)
    assert aggregate["cost_drag_bps"] == pytest.approx(1.4)
    assert group_aggregate["group_count"] == 3
    assert group_aggregate["executed_group_count"] == 2
    assert group_aggregate["weighted_total_return"] == pytest.approx(0.016)
    assert group_aggregate["weighted_cost_drag_bps"] == pytest.approx(1.4)
    assert group_aggregate["weighted_avg_leg_return_imbalance"] == pytest.approx(0.0036)
    assert group_aggregate["total_notional_usd"] == pytest.approx(1500.0)
    assert group_aggregate["weighted_notional_return"] == pytest.approx(0.014)
