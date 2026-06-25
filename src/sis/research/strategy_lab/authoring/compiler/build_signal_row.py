from __future__ import annotations

from datetime import datetime
from typing import Any

from sis.research.strategy_lab.authoring.compiler.build_entry_signal_rows import (
    _entry_signal_rows,
)
from sis.research.strategy_lab.authoring.compiler.build_trade_block_reasons import (
    _trade_block_reason_for_row,
)
from sis.research.strategy_lab.authoring.compiler.marker_dispatch import _marker_rule_signal_row
from sis.research.strategy_lab.authoring.compiler.marker_state_rows import _hold_signal_row
from sis.research.strategy_lab.authoring.compiler.signal_selection import (
    _rank_score,
    _score,
    _selected_side,
)
from sis.research.strategy_lab.authoring.contracts.spec import StrategyAuthoringSpec
from sis.research.strategy_lab.specs import SymbolBinding


def _build_signal_row(
    *,
    spec: StrategyAuthoringSpec,
    row: dict[str, Any],
    symbol: str,
    binding: SymbolBinding,
    bindings: dict[str, SymbolBinding],
    generated_at: datetime,
    cooldown_until_by_symbol: dict[str, datetime],
) -> list[dict[str, Any]]:
    marker_row = _marker_rule_signal_row(
        spec=spec,
        row=row,
        binding=binding,
        generated_at=generated_at,
    )
    if marker_row is not None:
        return [marker_row]

    signal_side, block_reason = _selected_side(row, spec.rules)
    if signal_side is None:
        return []
    if signal_side == "none":
        return [
            _hold_signal_row(
                spec=spec,
                row=row,
                binding=binding,
                generated_at=generated_at,
                block_reason=block_reason,
            )
        ]

    raw_score = _score(row, spec.rules.score)
    rank = _rank_score(raw_score)
    trade_block_reason = _trade_block_reason_for_row(
        row=row,
        spec=spec,
        symbol=symbol,
        cooldown_until_by_symbol=cooldown_until_by_symbol,
    )
    return _entry_signal_rows(
        spec=spec,
        row=row,
        binding=binding,
        bindings=bindings,
        side=signal_side,
        generated_at=generated_at,
        raw_score=raw_score,
        rank=rank,
        block_reason=trade_block_reason,
    )
