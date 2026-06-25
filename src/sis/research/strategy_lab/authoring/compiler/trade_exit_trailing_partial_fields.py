from __future__ import annotations

from typing import Any

from sis.research.strategy_lab.authoring.compiler.common import (
    _exit_override,
    _exit_override_column,
    _regime_value,
)
from sis.research.strategy_lab.authoring.compiler.row_numeric_values import _exit_bps
from sis.research.strategy_lab.authoring.compiler.trade_exit_partial_fields import (
    _trade_exit_partial_fields,
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
        **_trade_exit_partial_fields(
            row=row,
            exit_rules=exit_rules,
            regime=regime,
            exit_overrides=exit_overrides,
        ),
    }
