from __future__ import annotations

from datetime import datetime
from typing import Any

import polars as pl

from sis.research.strategy_lab.authoring.compiler.build_row_context import _row_symbol_binding
from sis.research.strategy_lab.authoring.compiler.build_signal_row import _build_signal_row
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
        rows.extend(
            _build_signal_row(
                spec=spec,
                row=row,
                symbol=symbol,
                binding=binding,
                bindings=bindings,
                generated_at=generated_at,
                cooldown_until_by_symbol=risk_throttle_cooldown_until_by_symbol,
            )
        )
    return rows
