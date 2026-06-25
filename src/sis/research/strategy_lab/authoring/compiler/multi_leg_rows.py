from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from sis.research.strategy_lab.authoring.compiler.multi_leg_base_sizing import (
    _multi_leg_base_sizing,
)
from sis.research.strategy_lab.authoring.compiler.multi_leg_signal_row import (
    _multi_leg_signal_row,
)
from sis.research.strategy_lab.authoring.compiler.signal_ids import _multi_leg_group_id
from sis.research.strategy_lab.authoring.contracts.spec import StrategyAuthoringSpec
from sis.research.strategy_lab.specs import SymbolBinding


def _multi_leg_signal_rows(
    *,
    spec: StrategyAuthoringSpec,
    row: dict[str, Any],
    bindings: dict[str, SymbolBinding],
    base_side: Literal["long", "short"],
    generated_at: datetime,
    raw_score: float | None,
    rank: float | None,
) -> list[dict[str, Any]]:
    base_sizing = _multi_leg_base_sizing(row=row, spec=spec)
    rows: list[dict[str, Any]] = []
    group_id = _multi_leg_group_id(spec, row, base_side=base_side)
    leg_count = len(spec.rules.multi_leg.legs)
    anchor_symbol = spec.rules.multi_leg.anchor_real_market_symbol
    for index, leg in enumerate(spec.rules.multi_leg.legs):
        binding = bindings[leg.real_market_symbol]
        rows.append(
            _multi_leg_signal_row(
                spec=spec,
                row=row,
                binding=binding,
                leg=leg,
                base_side=base_side,
                generated_at=generated_at,
                raw_score=raw_score,
                rank=rank,
                base_weight=base_sizing.position_weight,
                base_notional=base_sizing.notional_usd,
                group_id=group_id,
                leg_index=index + 1,
                leg_count=leg_count,
                anchor_symbol=anchor_symbol,
                default_entry_type=spec.rules.order.entry_type,
                default_time_in_force=spec.rules.order.time_in_force,
            )
        )
    return rows
