from __future__ import annotations

from types import SimpleNamespace

import polars as pl
import pytest

from sis.research.strategy_lab.authoring.contracts.base import StrategyAuthoringValidationError
from sis.research.strategy_lab.authoring.contracts.derived import DerivedFeature
from sis.research.strategy_lab.authoring.derived_cross_sectional import (
    CROSS_SECTIONAL_DERIVED_OPS,
    cross_sectional_expression,
)
from sis.research.strategy_lab.authoring.derived_execution_costs import (
    EXECUTION_COST_DERIVED_OPS,
    execution_cost_expression,
)
from sis.research.strategy_lab.authoring.derived_features import (
    apply_derived_features,
    derived_expression,
)


def test_apply_derived_features_computes_representative_ops() -> None:
    frame = pl.DataFrame(
        {
            "canonical_symbol": ["QQQ", "QQQ", "SPY", "SPY"],
            "ts": [1, 2, 1, 2],
            "close": [100.0, 110.0, 50.0, 55.0],
            "ret": [0.01, 0.02, 0.03, -0.01],
            "score": [3.0, 2.0, 1.0, 4.0],
        }
    )
    spec = SimpleNamespace(
        rules=SimpleNamespace(
            derived_features=[
                DerivedFeature(
                    name="rolling_return_1",
                    op="rolling_return",
                    columns=["close"],
                    window=1,
                    fill_null=0,
                ),
                DerivedFeature(
                    name="realized_var_2",
                    op="realized_variance",
                    columns=["ret"],
                    window=2,
                ),
                DerivedFeature(
                    name="score_rank",
                    op="cross_sectional_rank",
                    columns=["score"],
                ),
            ]
        )
    )

    result = apply_derived_features(frame, spec).sort(["canonical_symbol", "ts"])

    assert result.get_column("rolling_return_1").to_list() == pytest.approx([0.0, 0.1, 0.0, 0.1])
    assert result.get_column("realized_var_2").to_list() == pytest.approx(
        [0.0001, 0.00025, 0.0009, 0.0005]
    )
    assert result.sort(["ts", "canonical_symbol"]).get_column("score_rank").to_list() == [
        1.0,
        0.0,
        0.0,
        1.0,
    ]


def test_derived_expression_uses_null_for_zero_denominator() -> None:
    frame = pl.DataFrame({"canonical_symbol": ["QQQ"], "ts": [1], "left": [10.0], "right": [0.0]})
    feature = DerivedFeature(name="ratio", op="ratio", columns=["left", "right"])

    result = frame.with_columns(derived_expression(feature))

    assert result.get_column("ratio").to_list() == [None]


def test_derived_expression_rejects_unsupported_constructed_op() -> None:
    feature = DerivedFeature.model_construct(
        name="unsupported",
        op="unsupported",
        columns=["left"],
        value=None,
        window=None,
        fill_null=None,
    )

    with pytest.raises(StrategyAuthoringValidationError, match="Unsupported derived feature op"):
        derived_expression(feature)


def test_cross_sectional_expression_ranks_and_standardizes_by_timestamp() -> None:
    frame = pl.DataFrame(
        {
            "ts": [1, 1, 1],
            "canonical_symbol": ["AAA", "BBB", "CCC"],
            "score": [3.0, 1.0, 2.0],
        }
    )

    result = frame.with_columns(
        [
            cross_sectional_expression(
                DerivedFeature(name="rank", op="cross_sectional_rank", columns=["score"])
            ).alias("rank"),
            cross_sectional_expression(
                DerivedFeature(name="z", op="cross_sectional_zscore", columns=["score"])
            ).alias("z"),
            cross_sectional_expression(
                DerivedFeature(name="demean", op="cross_sectional_demean", columns=["score"])
            ).alias("demean"),
        ]
    ).sort("canonical_symbol")

    assert CROSS_SECTIONAL_DERIVED_OPS == {
        "cross_sectional_rank",
        "cross_sectional_zscore",
        "cross_sectional_demean",
        "group_cross_sectional_rank",
        "group_cross_sectional_zscore",
        "group_cross_sectional_demean",
    }
    assert result.get_column("rank").to_list() == pytest.approx([1.0, 0.0, 0.5])
    assert result.get_column("z").to_list() == pytest.approx([1.0, -1.0, 0.0])
    assert result.get_column("demean").to_list() == pytest.approx([1.0, -1.0, 0.0])


def test_cross_sectional_expression_handles_group_variants() -> None:
    frame = pl.DataFrame(
        {
            "ts": [1, 1, 1],
            "canonical_symbol": ["AAA", "BBB", "CCC"],
            "group": ["tech", "tech", "health"],
            "score": [3.0, 1.0, 2.0],
        }
    )

    result = frame.with_columns(
        [
            cross_sectional_expression(
                DerivedFeature(
                    name="rank",
                    op="group_cross_sectional_rank",
                    columns=["score", "group"],
                )
            ).alias("rank"),
            cross_sectional_expression(
                DerivedFeature(
                    name="z",
                    op="group_cross_sectional_zscore",
                    columns=["score", "group"],
                )
            ).alias("z"),
            cross_sectional_expression(
                DerivedFeature(
                    name="demean",
                    op="group_cross_sectional_demean",
                    columns=["score", "group"],
                )
            ).alias("demean"),
        ]
    ).sort("canonical_symbol")

    assert result.get_column("rank").to_list() == pytest.approx([1.0, 0.0, 1.0])
    z_values = result.get_column("z").to_list()
    assert z_values[:2] == pytest.approx([0.7071067812, -0.7071067812])
    assert z_values[2] is None
    assert result.get_column("demean").to_list() == pytest.approx([1.0, -1.0, 0.0])


def test_execution_cost_expression_computes_execution_constraint_ops() -> None:
    frame = pl.DataFrame(
        {
            "ahead": [2.0, 0.0],
            "behind": [6.0, 0.0],
            "latency_ms": [4.0, 2.0],
            "maker_fee": [1.0, 2.5],
            "taker_fee": [3.0, 2.0],
            "borrow_rate": [0.02, 0.01],
            "hold_years": [0.5, 2.0],
            "borrow_available": [40.0, 3.0],
            "borrow_needed": [80.0, 0.0],
            "tax_rate": [0.2, 0.3],
            "gain": [0.1, -0.2],
            "target_weight": [0.6, -0.25],
            "current_weight": [0.4, 0.1],
        }
    )

    result = frame.with_columns(
        [
            execution_cost_expression(
                DerivedFeature(
                    name="queue",
                    op="queue_position_score",
                    columns=["ahead", "behind"],
                )
            ).alias("queue"),
            execution_cost_expression(
                DerivedFeature(
                    name="latency",
                    op="latency_penalty_bps",
                    columns=["latency_ms"],
                    value=0.5,
                )
            ).alias("latency"),
            execution_cost_expression(
                DerivedFeature(
                    name="fee_edge",
                    op="maker_taker_fee_edge_bps",
                    columns=["maker_fee", "taker_fee"],
                )
            ).alias("fee_edge"),
            execution_cost_expression(
                DerivedFeature(
                    name="borrow_cost",
                    op="borrow_cost_bps",
                    columns=["borrow_rate", "hold_years"],
                )
            ).alias("borrow_cost"),
            execution_cost_expression(
                DerivedFeature(
                    name="borrow_availability",
                    op="borrow_availability_ratio",
                    columns=["borrow_available", "borrow_needed"],
                )
            ).alias("borrow_availability"),
            execution_cost_expression(
                DerivedFeature(
                    name="tax_drag",
                    op="tax_drag_bps",
                    columns=["tax_rate", "gain"],
                )
            ).alias("tax_drag"),
            execution_cost_expression(
                DerivedFeature(
                    name="rebalance",
                    op="rebalance_drift",
                    columns=["target_weight", "current_weight"],
                )
            ).alias("rebalance"),
        ]
    )

    assert EXECUTION_COST_DERIVED_OPS == {
        "queue_position_score",
        "latency_penalty_bps",
        "maker_taker_fee_edge_bps",
        "borrow_cost_bps",
        "borrow_availability_ratio",
        "tax_drag_bps",
        "rebalance_drift",
    }
    assert result.get_column("queue").to_list() == pytest.approx([0.75, None])
    assert result.get_column("latency").to_list() == pytest.approx([2.0, 1.0])
    assert result.get_column("fee_edge").to_list() == pytest.approx([2.0, -0.5])
    assert result.get_column("borrow_cost").to_list() == pytest.approx([100.0, 200.0])
    assert result.get_column("borrow_availability").to_list() == pytest.approx([0.5, None])
    assert result.get_column("tax_drag").to_list() == pytest.approx([200.0, -600.0])
    assert result.get_column("rebalance").to_list() == pytest.approx([0.2, 0.35])
