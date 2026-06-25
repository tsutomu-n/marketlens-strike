from __future__ import annotations

from typing import Any

from sis.research.strategy_lab.authoring.compiler.trade_bracket_fields import (
    _trade_bracket_fields,
)
from sis.research.strategy_lab.authoring.compiler.trade_execution_fields import (
    _trade_execution_fields,
)
from sis.research.strategy_lab.authoring.compiler.trade_exit_fields import _trade_exit_fields
from sis.research.strategy_lab.authoring.compiler.trade_order_fields import _trade_order_fields
from sis.research.strategy_lab.authoring.contracts.spec import StrategyAuthoringSpec


def _trade_control_fields(
    *,
    row: dict[str, Any],
    spec: StrategyAuthoringSpec,
    regime: Any = None,
    exit_overrides: dict[str, float | None] | None = None,
    order_overrides: dict[str, Any] | None = None,
    execution_overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    order_fields = _trade_order_fields(
        row=row,
        order=spec.rules.order,
        order_overrides=order_overrides,
    )
    execution_fields = _trade_execution_fields(
        row=row,
        execution=spec.rules.execution,
        regime=regime,
        execution_overrides=execution_overrides,
    )
    exit_fields = _trade_exit_fields(
        row=row,
        exit_rules=spec.rules.exit,
        reduce_only=bool(order_fields["entry_reduce_only"]),
        regime=regime,
        exit_overrides=exit_overrides,
    )
    return {
        **exit_fields,
        **_trade_bracket_fields(row=row, bracket=spec.rules.bracket),
        **order_fields,
        **execution_fields,
    }
