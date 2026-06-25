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
from sis.research.strategy_lab.authoring.compiler.trade_execution_risk_fields import (
    _trade_execution_risk_fields,
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
        **_trade_execution_risk_fields(
            row=row,
            execution=execution,
            regime=regime,
            execution_overrides=execution_overrides,
        ),
    }
