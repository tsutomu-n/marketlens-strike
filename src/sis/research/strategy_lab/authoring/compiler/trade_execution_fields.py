from __future__ import annotations

from typing import Any

from sis.research.strategy_lab.authoring.compiler.common import (
    _override_column,
    _override_value,
    _regime_value,
)
from sis.research.strategy_lab.authoring.compiler.row_values import (
    _exit_bps,
    _optional_float_from_row,
    _sizing_value,
)


def _trade_execution_fields(
    *,
    row: dict[str, Any],
    execution: Any,
    regime: Any = None,
    execution_overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "slippage_bps": _exit_bps(
            row,
            fixed=_override_value(
                execution_overrides,
                "slippage_bps",
                _regime_value(regime, "slippage_bps", execution.slippage_bps),
            ),
            column=_override_column(
                execution_overrides,
                "slippage_bps",
                execution.slippage_bps_column,
            ),
        )
        or 0.0,
        "max_fill_fraction": _sizing_value(
            row,
            fixed=_override_value(
                execution_overrides,
                "max_fill_fraction",
                _regime_value(regime, "max_fill_fraction", execution.max_fill_fraction),
            ),
            column=_override_column(
                execution_overrides,
                "max_fill_fraction",
                execution.max_fill_fraction_column,
            ),
        ),
        "min_fill_fraction": _sizing_value(
            row,
            fixed=_override_value(
                execution_overrides,
                "min_fill_fraction",
                _regime_value(regime, "min_fill_fraction", execution.min_fill_fraction),
            ),
            column=_override_column(
                execution_overrides,
                "min_fill_fraction",
                execution.min_fill_fraction_column,
            ),
        ),
        "max_spread_bps": _exit_bps(
            row,
            fixed=_override_value(
                execution_overrides,
                "max_spread_bps",
                _regime_value(regime, "max_spread_bps", execution.max_spread_bps),
            ),
            column=_override_column(
                execution_overrides,
                "max_spread_bps",
                execution.max_spread_bps_column,
            ),
        ),
        "min_depth_usd": _sizing_value(
            row,
            fixed=_override_value(
                execution_overrides,
                "min_depth_usd",
                _regime_value(regime, "min_depth_usd", execution.min_depth_usd),
            ),
            column=_override_column(
                execution_overrides,
                "min_depth_usd",
                execution.min_depth_usd_column,
            ),
        ),
        "depth_column": _override_value(
            execution_overrides,
            "depth_column",
            execution.depth_column,
        ),
        "depth_participation_rate": _override_value(
            execution_overrides,
            "depth_participation_rate",
            _regime_value(
                regime,
                "depth_participation_rate",
                execution.depth_participation_rate,
            ),
        ),
        "max_latency_ms": _sizing_value(
            row,
            fixed=_override_value(
                execution_overrides,
                "max_latency_ms",
                _regime_value(regime, "max_latency_ms", execution.max_latency_ms),
            ),
            column=_override_column(
                execution_overrides,
                "max_latency_ms",
                execution.max_latency_ms_column,
            ),
        ),
        "latency_ms": _optional_float_from_row(
            row,
            _override_value(execution_overrides, "latency_column", execution.latency_column),
        ),
        "min_queue_position_score": _sizing_value(
            row,
            fixed=_override_value(
                execution_overrides,
                "min_queue_position_score",
                _regime_value(
                    regime,
                    "min_queue_position_score",
                    execution.min_queue_position_score,
                ),
            ),
            column=_override_column(
                execution_overrides,
                "min_queue_position_score",
                execution.min_queue_position_score_column,
            ),
        ),
        "queue_position_score": _optional_float_from_row(
            row,
            _override_value(
                execution_overrides,
                "queue_position_score_column",
                execution.queue_position_score_column,
            ),
        ),
        "min_borrow_availability_ratio": _sizing_value(
            row,
            fixed=_override_value(
                execution_overrides,
                "min_borrow_availability_ratio",
                _regime_value(
                    regime,
                    "min_borrow_availability_ratio",
                    execution.min_borrow_availability_ratio,
                ),
            ),
            column=_override_column(
                execution_overrides,
                "min_borrow_availability_ratio",
                execution.min_borrow_availability_ratio_column,
            ),
        ),
        "borrow_availability_ratio": _optional_float_from_row(
            row,
            _override_value(
                execution_overrides,
                "borrow_availability_column",
                execution.borrow_availability_column,
            ),
        ),
        "max_borrow_cost_bps": _exit_bps(
            row,
            fixed=_override_value(
                execution_overrides,
                "max_borrow_cost_bps",
                _regime_value(regime, "max_borrow_cost_bps", execution.max_borrow_cost_bps),
            ),
            column=_override_column(
                execution_overrides,
                "max_borrow_cost_bps",
                execution.max_borrow_cost_bps_column,
            ),
        ),
        "borrow_cost_bps": _optional_float_from_row(
            row,
            _override_value(
                execution_overrides,
                "borrow_cost_column",
                execution.borrow_cost_column,
            ),
        ),
        "max_tax_drag_bps": _exit_bps(
            row,
            fixed=_override_value(
                execution_overrides,
                "max_tax_drag_bps",
                _regime_value(regime, "max_tax_drag_bps", execution.max_tax_drag_bps),
            ),
            column=_override_column(
                execution_overrides,
                "max_tax_drag_bps",
                execution.max_tax_drag_bps_column,
            ),
        ),
        "tax_drag_bps": _optional_float_from_row(
            row,
            _override_value(execution_overrides, "tax_drag_column", execution.tax_drag_column),
        ),
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
