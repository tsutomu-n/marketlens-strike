from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from sis.research.strategy_lab.authoring.compiler.multi_leg_side import _resolve_leg_side
from sis.research.strategy_lab.authoring.compiler.multi_leg_overrides import (
    _multi_leg_execution_overrides,
    _multi_leg_exit_overrides,
)
from sis.research.strategy_lab.authoring.compiler.multi_leg_order_overrides import (
    _multi_leg_order_overrides,
)
from sis.research.strategy_lab.authoring.compiler.multi_leg_sizing import (
    _multi_leg_sizing_fields,
)
from sis.research.strategy_lab.authoring.compiler.trade_rows import _trade_signal_row
from sis.research.strategy_lab.authoring.contracts.multi_leg import MultiLegEntry
from sis.research.strategy_lab.authoring.contracts.spec import StrategyAuthoringSpec
from sis.research.strategy_lab.specs import SymbolBinding


def _multi_leg_signal_row(
    *,
    spec: StrategyAuthoringSpec,
    row: dict[str, Any],
    binding: SymbolBinding,
    leg: MultiLegEntry,
    base_side: Literal["long", "short"],
    generated_at: datetime,
    raw_score: float | None,
    rank: float | None,
    base_weight: float | None,
    base_notional: float | None,
    group_id: str,
    leg_index: int,
    leg_count: int,
    anchor_symbol: str | None,
    default_entry_type: Literal["market", "limit", "stop_market"],
    default_time_in_force: Literal["gtc", "gtd", "ioc", "fok"],
) -> dict[str, Any]:
    leg_side = _resolve_leg_side(base_side, leg.side)
    sizing_fields = _multi_leg_sizing_fields(
        row=row,
        leg=leg,
        base_weight=base_weight,
        base_notional=base_notional,
    )
    return _trade_signal_row(
        spec=spec,
        row=row,
        binding=binding,
        side=leg_side,
        generated_at=generated_at,
        raw_score=raw_score,
        rank=rank,
        position_weight=sizing_fields["position_weight"],
        notional_usd=sizing_fields["notional_usd"],
        exit_overrides=_multi_leg_exit_overrides(row=row, leg=leg),
        order_overrides=_multi_leg_order_overrides(
            row=row,
            leg=leg,
            default_entry_type=default_entry_type,
            default_time_in_force=default_time_in_force,
        ),
        execution_overrides=_multi_leg_execution_overrides(row=row, leg=leg),
        multi_leg_group_id=group_id,
        multi_leg_leg_index=leg_index,
        multi_leg_leg_count=leg_count,
        multi_leg_anchor_real_market_symbol=anchor_symbol,
        reason_codes=[
            spec.rules.reason_code,
            "multi_leg",
            leg.reason_code or f"leg_{leg_index}",
        ],
    )
