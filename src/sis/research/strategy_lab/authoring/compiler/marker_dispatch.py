from __future__ import annotations

from datetime import datetime
from typing import Any

from sis.research.strategy_lab.authoring.compiler.marker_rows import (
    _add_signal_row,
    _rebalance_signal_row,
    _reduce_signal_row,
)
from sis.research.strategy_lab.authoring.compiler.marker_state_rows import (
    _close_signal_row,
    _hold_signal_row,
)
from sis.research.strategy_lab.authoring.compiler.signal_selection import _entry_passes
from sis.research.strategy_lab.authoring.contracts.spec import StrategyAuthoringSpec
from sis.research.strategy_lab.specs import SymbolBinding


def _marker_rule_signal_row(
    *,
    spec: StrategyAuthoringSpec,
    row: dict[str, Any],
    binding: SymbolBinding,
    generated_at: datetime,
) -> dict[str, Any] | None:
    if spec.rules.close is not None and _entry_passes(row, spec.rules.close):
        return _close_signal_row(
            spec=spec,
            row=row,
            binding=binding,
            generated_at=generated_at,
        )
    if spec.rules.reduce is not None and _entry_passes(row, spec.rules.reduce):
        return _reduce_signal_row(
            spec=spec,
            row=row,
            binding=binding,
            generated_at=generated_at,
        )
    if spec.rules.add is not None and _entry_passes(row, spec.rules.add):
        return _add_signal_row(
            spec=spec,
            row=row,
            binding=binding,
            generated_at=generated_at,
        )
    if spec.rules.rebalance is not None and _entry_passes(row, spec.rules.rebalance):
        return _rebalance_signal_row(
            spec=spec,
            row=row,
            binding=binding,
            generated_at=generated_at,
        )
    if spec.rules.hold is not None and _entry_passes(row, spec.rules.hold):
        return _hold_signal_row(
            spec=spec,
            row=row,
            binding=binding,
            generated_at=generated_at,
            block_reason="hold_rule",
        )
    return None
