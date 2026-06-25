from __future__ import annotations

from typing import Any

from sis.research.strategy_lab.authoring.compiler.common import (
    _exit_override,
    _exit_override_column,
    _regime_value,
)
from sis.research.strategy_lab.authoring.compiler.row_values import (
    _exit_bps,
    _minutes_value,
    _sizing_value,
)


def _trade_exit_fields(
    *,
    row: dict[str, Any],
    exit_rules: Any,
    reduce_only: bool,
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
        "min_holding_minutes": _minutes_value(
            row,
            fixed=exit_rules.min_holding_minutes,
            column=exit_rules.min_holding_minutes_column,
        ),
        "max_holding_minutes": _minutes_value(
            row,
            fixed=exit_rules.max_holding_minutes,
            column=exit_rules.max_holding_minutes_column,
        ),
        "exit_priority": ",".join(exit_rules.exit_priority),
        "exit_on_opposite_signal": exit_rules.exit_on_opposite_signal,
        "exit_on_close_signal": exit_rules.exit_on_close_signal,
        "exit_on_reduce_signal": exit_rules.exit_on_reduce_signal,
        "reduce_fraction": _sizing_value(
            row,
            fixed=exit_rules.reduce_fraction if reduce_only else None,
            column=(exit_rules.reduce_fraction_column if reduce_only else None),
        ),
        "exit_on_add_signal": exit_rules.exit_on_add_signal,
        "add_fraction": None,
        "exit_on_rebalance_signal": exit_rules.exit_on_rebalance_signal,
        "rebalance_target_fraction": None,
        "rebalance_min_delta_fraction": None,
    }
