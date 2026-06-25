from __future__ import annotations

from typing import Any

from sis.research.strategy_lab.authoring.compiler.common import (
    _exit_override,
    _exit_override_column,
    _regime_value,
)
from sis.research.strategy_lab.authoring.compiler.row_numeric_values import _exit_bps


def _trade_exit_stop_fields(
    *,
    row: dict[str, Any],
    exit_rules: Any,
    regime: Any = None,
    exit_overrides: dict[str, float | None] | None = None,
) -> dict[str, Any]:
    return {
        "stop_loss_bps": _exit_bps(
            row,
            fixed=_exit_override(
                exit_overrides,
                "stop_loss_bps",
                _regime_value(regime, "stop_loss_bps", exit_rules.stop_loss_bps),
            ),
            column=_exit_override_column(
                exit_overrides, "stop_loss_bps", exit_rules.stop_loss_bps_column
            ),
        ),
        "min_stop_loss_bps": _exit_bps(
            row,
            fixed=_exit_override(
                exit_overrides,
                "min_stop_loss_bps",
                _regime_value(regime, "min_stop_loss_bps", exit_rules.min_stop_loss_bps),
            ),
            column=_exit_override_column(
                exit_overrides,
                "min_stop_loss_bps",
                exit_rules.min_stop_loss_bps_column,
            ),
        ),
        "max_stop_loss_bps": _exit_bps(
            row,
            fixed=_exit_override(
                exit_overrides,
                "max_stop_loss_bps",
                _regime_value(regime, "max_stop_loss_bps", exit_rules.max_stop_loss_bps),
            ),
            column=_exit_override_column(
                exit_overrides,
                "max_stop_loss_bps",
                exit_rules.max_stop_loss_bps_column,
            ),
        ),
    }
