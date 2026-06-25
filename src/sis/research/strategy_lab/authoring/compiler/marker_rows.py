from __future__ import annotations

from datetime import datetime
from typing import Any

from sis.research.strategy_lab.authoring.compiler.marker_action_row import (
    _marker_action_signal_row,
)
from sis.research.strategy_lab.authoring.compiler.marker_position_fields import (
    _marker_add_fields,
    _marker_rebalance_fields,
    _marker_reduce_fields,
)
from sis.research.strategy_lab.authoring.compiler.marker_state_rows import (
    _close_signal_row as _close_signal_row,
    _hold_signal_row as _hold_signal_row,
)
from sis.research.strategy_lab.authoring.contracts.spec import StrategyAuthoringSpec
from sis.research.strategy_lab.specs import SymbolBinding


def _reduce_signal_row(
    *,
    spec: StrategyAuthoringSpec,
    row: dict[str, Any],
    binding: SymbolBinding,
    generated_at: datetime,
) -> dict[str, Any]:
    return _marker_action_signal_row(
        spec=spec,
        row=row,
        binding=binding,
        generated_at=generated_at,
        side="reduce",
        position_fields=_marker_reduce_fields(row=row, spec=spec),
        reason_code=spec.rules.reduce_reason_code,
    )


def _add_signal_row(
    *,
    spec: StrategyAuthoringSpec,
    row: dict[str, Any],
    binding: SymbolBinding,
    generated_at: datetime,
) -> dict[str, Any]:
    return _marker_action_signal_row(
        spec=spec,
        row=row,
        binding=binding,
        generated_at=generated_at,
        side="add",
        position_fields=_marker_add_fields(row=row, spec=spec),
        reason_code=spec.rules.add_reason_code,
    )


def _rebalance_signal_row(
    *,
    spec: StrategyAuthoringSpec,
    row: dict[str, Any],
    binding: SymbolBinding,
    generated_at: datetime,
) -> dict[str, Any]:
    return _marker_action_signal_row(
        spec=spec,
        row=row,
        binding=binding,
        generated_at=generated_at,
        side="rebalance",
        position_fields=_marker_rebalance_fields(row=row, spec=spec),
        reason_code=spec.rules.rebalance_reason_code,
    )
