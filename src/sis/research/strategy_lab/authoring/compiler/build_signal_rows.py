from __future__ import annotations

from datetime import datetime
from typing import Any

import polars as pl

from sis.research.strategy_lab.authoring.compiler.build_row_context import (
    _row_symbol_binding,
)
from sis.research.strategy_lab.authoring.compiler.build_trade_block_reasons import (
    _trade_block_reason_for_row,
)
from sis.research.strategy_lab.authoring.compiler.marker_dispatch import _marker_rule_signal_row
from sis.research.strategy_lab.authoring.compiler.marker_state_rows import _hold_signal_row
from sis.research.strategy_lab.authoring.compiler.multi_leg_rows import _multi_leg_signal_rows
from sis.research.strategy_lab.authoring.compiler.signal_selection import (
    _rank_score,
    _score,
    _selected_side,
)
from sis.research.strategy_lab.authoring.compiler.trade_block_rows import _blocked_trade_signal_row
from sis.research.strategy_lab.authoring.compiler.trade_rows import _trade_signal_row
from sis.research.strategy_lab.authoring.contracts.spec import StrategyAuthoringSpec


def _build_signal_rows(
    *,
    spec: StrategyAuthoringSpec,
    feature: pl.DataFrame,
    generated_at: datetime,
) -> list[dict[str, Any]]:
    bindings = {binding.real_market_symbol: binding for binding in spec.experiment.symbol_bindings}
    rows: list[dict[str, Any]] = []
    risk_throttle_cooldown_until_by_symbol: dict[str, datetime] = {}
    for row in feature.sort(["canonical_symbol", "ts"]).to_dicts():
        resolved = _row_symbol_binding(row=row, spec=spec, bindings=bindings)
        if resolved is None:
            continue
        symbol, binding = resolved
        marker_row = _marker_rule_signal_row(
            spec=spec,
            row=row,
            binding=binding,
            generated_at=generated_at,
        )
        if marker_row is not None:
            rows.append(marker_row)
            continue
        signal_side, block_reason = _selected_side(row, spec.rules)
        if signal_side is None:
            continue
        if signal_side == "none":
            rows.append(
                _hold_signal_row(
                    spec=spec,
                    row=row,
                    binding=binding,
                    generated_at=generated_at,
                    block_reason=block_reason,
                )
            )
            continue
        raw_score = _score(row, spec.rules.score)
        rank = _rank_score(raw_score)
        block_reason = _trade_block_reason_for_row(
            row=row,
            spec=spec,
            symbol=symbol,
            cooldown_until_by_symbol=risk_throttle_cooldown_until_by_symbol,
        )
        if block_reason is not None:
            rows.append(
                _blocked_trade_signal_row(
                    spec=spec,
                    row=row,
                    binding=binding,
                    side=signal_side,
                    generated_at=generated_at,
                    raw_score=raw_score,
                    rank=rank,
                    block_reason=block_reason,
                )
            )
            continue
        if spec.rules.multi_leg.enabled:
            rows.extend(
                _multi_leg_signal_rows(
                    spec=spec,
                    row=row,
                    bindings=bindings,
                    base_side=signal_side,
                    generated_at=generated_at,
                    raw_score=raw_score,
                    rank=rank,
                )
            )
        else:
            rows.append(
                _trade_signal_row(
                    spec=spec,
                    row=row,
                    binding=binding,
                    side=signal_side,
                    generated_at=generated_at,
                    raw_score=raw_score,
                    rank=rank,
                )
            )
    return rows
