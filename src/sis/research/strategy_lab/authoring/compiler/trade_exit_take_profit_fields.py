from __future__ import annotations

from typing import Any

from sis.research.strategy_lab.authoring.compiler.common import (
    _exit_override,
    _exit_override_column,
    _regime_value,
)
from sis.research.strategy_lab.authoring.compiler.row_values import _exit_bps


def _trade_exit_take_profit_fields(
    *,
    row: dict[str, Any],
    exit_rules: Any,
    regime: Any = None,
    exit_overrides: dict[str, float | None] | None = None,
) -> dict[str, Any]:
    return {
        "take_profit_bps": _exit_bps(
            row,
            fixed=_exit_override(
                exit_overrides,
                "take_profit_bps",
                _regime_value(regime, "take_profit_bps", exit_rules.take_profit_bps),
            ),
            column=_exit_override_column(
                exit_overrides, "take_profit_bps", exit_rules.take_profit_bps_column
            ),
        ),
        "min_take_profit_bps": _exit_bps(
            row,
            fixed=_exit_override(
                exit_overrides,
                "min_take_profit_bps",
                _regime_value(
                    regime,
                    "min_take_profit_bps",
                    exit_rules.min_take_profit_bps,
                ),
            ),
            column=_exit_override_column(
                exit_overrides,
                "min_take_profit_bps",
                exit_rules.min_take_profit_bps_column,
            ),
        ),
        "max_take_profit_bps": _exit_bps(
            row,
            fixed=_exit_override(
                exit_overrides,
                "max_take_profit_bps",
                _regime_value(
                    regime,
                    "max_take_profit_bps",
                    exit_rules.max_take_profit_bps,
                ),
            ),
            column=_exit_override_column(
                exit_overrides,
                "max_take_profit_bps",
                exit_rules.max_take_profit_bps_column,
            ),
        ),
    }
