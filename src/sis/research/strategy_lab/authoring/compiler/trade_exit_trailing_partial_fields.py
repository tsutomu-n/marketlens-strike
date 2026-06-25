from __future__ import annotations

from typing import Any

from sis.research.strategy_lab.authoring.compiler.common import (
    _exit_override,
    _exit_override_column,
    _regime_value,
)
from sis.research.strategy_lab.authoring.compiler.row_values import (
    _exit_bps,
    _sizing_value,
)


def _trade_exit_trailing_partial_fields(
    *,
    row: dict[str, Any],
    exit_rules: Any,
    regime: Any = None,
    exit_overrides: dict[str, float | None] | None = None,
) -> dict[str, Any]:
    return {
        "trailing_stop_bps": _exit_bps(
            row,
            fixed=_exit_override(
                exit_overrides,
                "trailing_stop_bps",
                _regime_value(regime, "trailing_stop_bps", exit_rules.trailing_stop_bps),
            ),
            column=_exit_override_column(
                exit_overrides, "trailing_stop_bps", exit_rules.trailing_stop_bps_column
            ),
        ),
        "trailing_stop_activation_bps": _exit_bps(
            row,
            fixed=_exit_override(
                exit_overrides,
                "trailing_stop_activation_bps",
                _regime_value(
                    regime,
                    "trailing_stop_activation_bps",
                    exit_rules.trailing_stop_activation_bps,
                ),
            ),
            column=_exit_override_column(
                exit_overrides,
                "trailing_stop_activation_bps",
                exit_rules.trailing_stop_activation_bps_column,
            ),
        ),
        "partial_take_profit_bps": _exit_bps(
            row,
            fixed=_exit_override(
                exit_overrides,
                "partial_take_profit_bps",
                _regime_value(
                    regime,
                    "partial_take_profit_bps",
                    exit_rules.partial_take_profit_bps,
                ),
            ),
            column=_exit_override_column(
                exit_overrides,
                "partial_take_profit_bps",
                exit_rules.partial_take_profit_bps_column,
            ),
        ),
        "partial_exit_fraction": _sizing_value(
            row,
            fixed=_exit_override(
                exit_overrides,
                "partial_exit_fraction",
                _regime_value(
                    regime,
                    "partial_exit_fraction",
                    exit_rules.partial_exit_fraction,
                ),
            ),
            column=_exit_override_column(
                exit_overrides,
                "partial_exit_fraction",
                exit_rules.partial_exit_fraction_column,
            ),
        ),
    }
