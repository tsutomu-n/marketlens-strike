from __future__ import annotations

from typing import Any

from sis.research.strategy_lab.authoring.compiler.trade_exit_bracket_fields import (
    _trade_exit_bracket_fields,
)
from sis.research.strategy_lab.authoring.compiler.row_values import (
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
        **_trade_exit_bracket_fields(
            row=row,
            exit_rules=exit_rules,
            regime=regime,
            exit_overrides=exit_overrides,
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
