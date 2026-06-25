from __future__ import annotations

from typing import Any

from sis.research.strategy_lab.authoring.compiler.common import (
    _override_column,
    _override_value,
    _regime_value,
)
from sis.research.strategy_lab.authoring.compiler.row_values import (
    _optional_float_from_row,
    _sizing_value,
)


def _trade_execution_pressure_fields(
    *,
    row: dict[str, Any],
    execution: Any,
    regime: Any = None,
    execution_overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "max_turnover_pressure": _sizing_value(
            row,
            fixed=_override_value(
                execution_overrides,
                "max_turnover_pressure",
                _regime_value(
                    regime,
                    "max_turnover_pressure",
                    execution.max_turnover_pressure,
                ),
            ),
            column=_override_column(
                execution_overrides,
                "max_turnover_pressure",
                execution.max_turnover_pressure_column,
            ),
        ),
        "turnover_pressure": _optional_float_from_row(
            row,
            _override_value(
                execution_overrides,
                "turnover_pressure_column",
                execution.turnover_pressure_column,
            ),
        ),
        "max_capacity_usage_ratio": _sizing_value(
            row,
            fixed=_override_value(
                execution_overrides,
                "max_capacity_usage_ratio",
                _regime_value(
                    regime,
                    "max_capacity_usage_ratio",
                    execution.max_capacity_usage_ratio,
                ),
            ),
            column=_override_column(
                execution_overrides,
                "max_capacity_usage_ratio",
                execution.max_capacity_usage_ratio_column,
            ),
        ),
        "capacity_usage_ratio": _optional_float_from_row(
            row,
            _override_value(
                execution_overrides,
                "capacity_usage_column",
                execution.capacity_usage_column,
            ),
        ),
        "max_correlation_crowding_score": _sizing_value(
            row,
            fixed=_override_value(
                execution_overrides,
                "max_correlation_crowding_score",
                _regime_value(
                    regime,
                    "max_correlation_crowding_score",
                    execution.max_correlation_crowding_score,
                ),
            ),
            column=_override_column(
                execution_overrides,
                "max_correlation_crowding_score",
                execution.max_correlation_crowding_score_column,
            ),
        ),
        "correlation_crowding_score": _optional_float_from_row(
            row,
            _override_value(
                execution_overrides,
                "correlation_crowding_column",
                execution.correlation_crowding_column,
            ),
        ),
        "min_fee_edge_bps": _sizing_value(
            row,
            fixed=_override_value(
                execution_overrides,
                "min_fee_edge_bps",
                _regime_value(regime, "min_fee_edge_bps", execution.min_fee_edge_bps),
            ),
            column=_override_column(
                execution_overrides,
                "min_fee_edge_bps",
                execution.min_fee_edge_bps_column,
            ),
        ),
        "fee_edge_bps": _optional_float_from_row(
            row,
            _override_value(execution_overrides, "fee_edge_column", execution.fee_edge_column),
        ),
    }
