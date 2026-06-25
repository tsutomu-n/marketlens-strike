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


def _trade_exit_primary_bracket_fields(
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
        "min_reward_risk_ratio": _sizing_value(
            row,
            fixed=_exit_override(
                exit_overrides,
                "min_reward_risk_ratio",
                _regime_value(
                    regime,
                    "min_reward_risk_ratio",
                    exit_rules.min_reward_risk_ratio,
                ),
            ),
            column=_exit_override_column(
                exit_overrides,
                "min_reward_risk_ratio",
                exit_rules.min_reward_risk_ratio_column,
            ),
        ),
        "reward_risk_ratio": None,
    }
