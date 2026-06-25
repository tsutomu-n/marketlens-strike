from __future__ import annotations

from typing import Any

from sis.research.strategy_lab.authoring.compiler.common import (
    _exit_override,
    _exit_override_column,
    _regime_value,
)
from sis.research.strategy_lab.authoring.compiler.row_values import _sizing_value


def _trade_exit_reward_risk_fields(
    *,
    row: dict[str, Any],
    exit_rules: Any,
    regime: Any = None,
    exit_overrides: dict[str, float | None] | None = None,
) -> dict[str, Any]:
    return {
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
