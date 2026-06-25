from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from sis.research.strategy_lab.authoring.compiler.common import (
    _resolve_leg_side,
)
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
from sis.research.strategy_lab.authoring.compiler.row_values import _sizing_value
from sis.research.strategy_lab.authoring.compiler.signal_sizing import (
    _signal_notional_usd,
    _signal_position_weight,
)
from sis.research.strategy_lab.authoring.compiler.signal_ids import _multi_leg_group_id
from sis.research.strategy_lab.authoring.compiler.trade_rows import _trade_signal_row
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
    base_weight = _sizing_value(
        row,
        fixed=_signal_position_weight(row, spec),
        column=None,
    )
    base_notional = _sizing_value(
        row,
        fixed=_signal_notional_usd(row, spec),
        column=None,
    )
    rows: list[dict[str, Any]] = []
    group_id = _multi_leg_group_id(spec, row, base_side=base_side)
    leg_count = len(spec.rules.multi_leg.legs)
    anchor_symbol = spec.rules.multi_leg.anchor_real_market_symbol
    for index, leg in enumerate(spec.rules.multi_leg.legs):
        binding = bindings[leg.real_market_symbol]
        leg_side = _resolve_leg_side(base_side, leg.side)
        sizing_fields = _multi_leg_sizing_fields(
            row=row,
            leg=leg,
            base_weight=base_weight,
            base_notional=base_notional,
        )
        exit_overrides = _multi_leg_exit_overrides(row=row, leg=leg)
        order_overrides = _multi_leg_order_overrides(
            row=row,
            leg=leg,
            default_entry_type=spec.rules.order.entry_type,
            default_time_in_force=spec.rules.order.time_in_force,
        )
        execution_overrides = _multi_leg_execution_overrides(row=row, leg=leg)
        rows.append(
            _trade_signal_row(
                spec=spec,
                row=row,
                binding=binding,
                side=leg_side,
                generated_at=generated_at,
                raw_score=raw_score,
                rank=rank,
                position_weight=sizing_fields["position_weight"],
                notional_usd=sizing_fields["notional_usd"],
                exit_overrides=exit_overrides,
                order_overrides=order_overrides,
                execution_overrides=execution_overrides,
                multi_leg_group_id=group_id,
                multi_leg_leg_index=index + 1,
                multi_leg_leg_count=leg_count,
                multi_leg_anchor_real_market_symbol=anchor_symbol,
                reason_codes=[
                    spec.rules.reason_code,
                    "multi_leg",
                    leg.reason_code or f"leg_{index + 1}",
                ],
            )
        )
    return rows
