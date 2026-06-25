from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from sis.research.strategy_lab.authoring.compiler.multi_leg_rows import _multi_leg_signal_rows
from sis.research.strategy_lab.authoring.compiler.trade_block_rows import _blocked_trade_signal_row
from sis.research.strategy_lab.authoring.compiler.trade_rows import _trade_signal_row
from sis.research.strategy_lab.authoring.contracts.spec import StrategyAuthoringSpec
from sis.research.strategy_lab.specs import SymbolBinding


def _entry_signal_rows(
    *,
    spec: StrategyAuthoringSpec,
    row: dict[str, Any],
    binding: SymbolBinding,
    bindings: dict[str, SymbolBinding],
    side: Literal["long", "short"],
    generated_at: datetime,
    raw_score: float | None,
    rank: float | None,
    block_reason: str | None,
) -> list[dict[str, Any]]:
    if block_reason is not None:
        return [
            _blocked_trade_signal_row(
                spec=spec,
                row=row,
                binding=binding,
                side=side,
                generated_at=generated_at,
                raw_score=raw_score,
                rank=rank,
                block_reason=block_reason,
            )
        ]
    if spec.rules.multi_leg.enabled:
        return _multi_leg_signal_rows(
            spec=spec,
            row=row,
            bindings=bindings,
            base_side=side,
            generated_at=generated_at,
            raw_score=raw_score,
            rank=rank,
        )
    return [
        _trade_signal_row(
            spec=spec,
            row=row,
            binding=binding,
            side=side,
            generated_at=generated_at,
            raw_score=raw_score,
            rank=rank,
        )
    ]
