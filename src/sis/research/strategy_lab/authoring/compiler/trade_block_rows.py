from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from sis.research.strategy_lab.authoring.compiler.common import _block_trade_row
from sis.research.strategy_lab.authoring.compiler.trade_rows import _trade_signal_row
from sis.research.strategy_lab.authoring.contracts.spec import StrategyAuthoringSpec
from sis.research.strategy_lab.specs import SymbolBinding


def _blocked_trade_signal_row(
    *,
    spec: StrategyAuthoringSpec,
    row: dict[str, Any],
    binding: SymbolBinding,
    side: Literal["long", "short"],
    generated_at: datetime,
    raw_score: float | None,
    rank: float | None,
    block_reason: str,
) -> dict[str, Any]:
    return _block_trade_row(
        _trade_signal_row(
            spec=spec,
            row=row,
            binding=binding,
            side=side,
            generated_at=generated_at,
            raw_score=raw_score,
            rank=rank,
        ),
        spec=spec,
        block_reason=block_reason,
    )
