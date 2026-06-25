from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from sis.research.strategy_lab.authoring.compiler.common import (
    _matching_regime_override,
)
from sis.research.strategy_lab.authoring.compiler.trade_control_fields import (
    _trade_control_fields,
)
from sis.research.strategy_lab.authoring.compiler.trade_identity_fields import (
    _trade_identity_fields,
)
from sis.research.strategy_lab.authoring.compiler.trade_portfolio_fields import (
    _trade_portfolio_fields,
)
from sis.research.strategy_lab.authoring.compiler.trade_reason_fields import (
    _trade_reason_fields,
)
from sis.research.strategy_lab.authoring.compiler.trade_score_fields import (
    _trade_score_fields,
)
from sis.research.strategy_lab.authoring.compiler.trade_sizing_fields import (
    _trade_sizing_fields,
)
from sis.research.strategy_lab.authoring.contracts.spec import StrategyAuthoringSpec
from sis.research.strategy_lab.specs import SymbolBinding


def _trade_signal_row(
    *,
    spec: StrategyAuthoringSpec,
    row: dict[str, Any],
    binding: SymbolBinding,
    side: Literal["long", "short"],
    generated_at: datetime,
    raw_score: float | None,
    rank: float | None,
    position_weight: float | None = None,
    notional_usd: float | None = None,
    exit_overrides: dict[str, float | None] | None = None,
    order_overrides: dict[str, Any] | None = None,
    execution_overrides: dict[str, Any] | None = None,
    multi_leg_group_id: str | None = None,
    multi_leg_leg_index: int | None = None,
    multi_leg_leg_count: int | None = None,
    multi_leg_anchor_real_market_symbol: str | None = None,
    reason_codes: list[str] | None = None,
) -> dict[str, Any]:
    regime = _matching_regime_override(row, spec)
    return {
        **_trade_identity_fields(
            spec=spec,
            row=row,
            binding=binding,
            side=side,
            generated_at=generated_at,
            multi_leg_group_id=multi_leg_group_id,
            multi_leg_leg_index=multi_leg_leg_index,
            multi_leg_leg_count=multi_leg_leg_count,
            multi_leg_anchor_real_market_symbol=multi_leg_anchor_real_market_symbol,
        ),
        **_trade_score_fields(spec=spec, row=row, raw_score=raw_score, rank=rank),
        **_trade_control_fields(
            row=row,
            spec=spec,
            regime=regime,
            exit_overrides=exit_overrides,
            order_overrides=order_overrides,
            execution_overrides=execution_overrides,
        ),
        **_trade_sizing_fields(
            spec=spec,
            row=row,
            position_weight=position_weight,
            notional_usd=notional_usd,
        ),
        **_trade_portfolio_fields(row=row, spec=spec),
        **_trade_reason_fields(spec=spec, regime=regime, reason_codes=reason_codes),
    }
