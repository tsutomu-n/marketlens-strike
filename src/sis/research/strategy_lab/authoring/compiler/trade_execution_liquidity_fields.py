from __future__ import annotations

from typing import Any

from sis.research.strategy_lab.authoring.compiler.common import (
    _override_column,
    _override_value,
    _regime_value,
)
from sis.research.strategy_lab.authoring.compiler.row_numeric_values import (
    _exit_bps,
    _sizing_value,
)


def _trade_execution_liquidity_fields(
    *,
    row: dict[str, Any],
    execution: Any,
    regime: Any = None,
    execution_overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
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
    }
