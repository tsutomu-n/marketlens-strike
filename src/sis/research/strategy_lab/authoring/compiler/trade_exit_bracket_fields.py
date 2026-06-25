from __future__ import annotations

from typing import Any

from sis.research.strategy_lab.authoring.compiler.trade_exit_primary_bracket_fields import (
    _trade_exit_primary_bracket_fields,
)
from sis.research.strategy_lab.authoring.compiler.trade_exit_trailing_partial_fields import (
    _trade_exit_trailing_partial_fields,
)


def _trade_exit_bracket_fields(
    *,
    row: dict[str, Any],
    exit_rules: Any,
    regime: Any = None,
    exit_overrides: dict[str, float | None] | None = None,
) -> dict[str, Any]:
    return {
        **_trade_exit_primary_bracket_fields(
            row=row,
            exit_rules=exit_rules,
            regime=regime,
            exit_overrides=exit_overrides,
        ),
        **_trade_exit_trailing_partial_fields(
            row=row,
            exit_rules=exit_rules,
            regime=regime,
            exit_overrides=exit_overrides,
        ),
    }
