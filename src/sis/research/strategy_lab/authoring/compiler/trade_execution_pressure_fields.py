from __future__ import annotations

from typing import Any

from sis.research.strategy_lab.authoring.compiler.trade_execution_pressure_values import (
    _execution_pressure_limit_value,
    _execution_pressure_observed_value,
)

_PRESSURE_FIELD_PAIRS: tuple[tuple[str, str, str, str, str, str], ...] = (
    (
        "max_turnover_pressure",
        "max_turnover_pressure",
        "max_turnover_pressure_column",
        "turnover_pressure",
        "turnover_pressure_column",
        "turnover_pressure_column",
    ),
    (
        "max_capacity_usage_ratio",
        "max_capacity_usage_ratio",
        "max_capacity_usage_ratio_column",
        "capacity_usage_ratio",
        "capacity_usage_column",
        "capacity_usage_column",
    ),
    (
        "max_correlation_crowding_score",
        "max_correlation_crowding_score",
        "max_correlation_crowding_score_column",
        "correlation_crowding_score",
        "correlation_crowding_column",
        "correlation_crowding_column",
    ),
    (
        "min_fee_edge_bps",
        "min_fee_edge_bps",
        "min_fee_edge_bps_column",
        "fee_edge_bps",
        "fee_edge_column",
        "fee_edge_column",
    ),
)


def _trade_execution_pressure_fields(
    *,
    row: dict[str, Any],
    execution: Any,
    regime: Any = None,
    execution_overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    fields: dict[str, Any] = {}
    for (
        limit_output,
        limit_value_attr,
        limit_column_attr,
        observed_output,
        observed_override_column_key,
        observed_column_attr,
    ) in _PRESSURE_FIELD_PAIRS:
        fields[limit_output] = _execution_pressure_limit_value(
            row=row,
            execution=execution,
            regime=regime,
            execution_overrides=execution_overrides,
            value_attr=limit_value_attr,
            column_attr=limit_column_attr,
        )
        fields[observed_output] = _execution_pressure_observed_value(
            row=row,
            execution=execution,
            execution_overrides=execution_overrides,
            override_column_key=observed_override_column_key,
            column_attr=observed_column_attr,
        )
    return fields
