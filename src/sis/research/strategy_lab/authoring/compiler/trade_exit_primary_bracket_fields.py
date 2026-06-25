from __future__ import annotations

from typing import Any

from sis.research.strategy_lab.authoring.compiler.trade_exit_reward_risk_fields import (
    _trade_exit_reward_risk_fields,
)
from sis.research.strategy_lab.authoring.compiler.trade_exit_stop_fields import (
    _trade_exit_stop_fields,
)
from sis.research.strategy_lab.authoring.compiler.trade_exit_take_profit_fields import (
    _trade_exit_take_profit_fields,
)


def _trade_exit_primary_bracket_fields(
    *,
    row: dict[str, Any],
    exit_rules: Any,
    regime: Any = None,
    exit_overrides: dict[str, float | None] | None = None,
) -> dict[str, Any]:
    return {
        **_trade_exit_stop_fields(
            row=row,
            exit_rules=exit_rules,
            regime=regime,
            exit_overrides=exit_overrides,
        ),
        **_trade_exit_take_profit_fields(
            row=row,
            exit_rules=exit_rules,
            regime=regime,
            exit_overrides=exit_overrides,
        ),
        **_trade_exit_reward_risk_fields(
            row=row,
            exit_rules=exit_rules,
            regime=regime,
            exit_overrides=exit_overrides,
        ),
    }
