from __future__ import annotations

from typing import Any

from sis.research.strategy_lab.authoring.compiler.row_values import _sizing_value
from sis.research.strategy_lab.authoring.contracts.spec import StrategyAuthoringSpec


def _marker_reduce_fields(
    *, row: dict[str, Any], spec: StrategyAuthoringSpec
) -> dict[str, float | None]:
    return {
        "reduce_fraction": _sizing_value(
            row,
            fixed=spec.rules.exit.reduce_fraction,
            column=spec.rules.exit.reduce_fraction_column,
        )
    }


def _marker_add_fields(
    *, row: dict[str, Any], spec: StrategyAuthoringSpec
) -> dict[str, float | None]:
    return {
        "add_fraction": _sizing_value(
            row,
            fixed=spec.rules.exit.add_fraction,
            column=spec.rules.exit.add_fraction_column,
        )
    }


def _marker_rebalance_fields(
    *, row: dict[str, Any], spec: StrategyAuthoringSpec
) -> dict[str, float | None]:
    return {
        "rebalance_target_fraction": _sizing_value(
            row,
            fixed=spec.rules.exit.rebalance_target_fraction,
            column=spec.rules.exit.rebalance_target_fraction_column,
        ),
        "rebalance_min_delta_fraction": _sizing_value(
            row,
            fixed=spec.rules.exit.rebalance_min_delta_fraction,
            column=spec.rules.exit.rebalance_min_delta_fraction_column,
        ),
    }
