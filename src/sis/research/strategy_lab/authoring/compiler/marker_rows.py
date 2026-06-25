from __future__ import annotations

from datetime import datetime
from typing import Any

from sis.research.strategy_lab.authoring.compiler.marker_defaults import (
    _marker_trade_control_defaults,
)
from sis.research.strategy_lab.authoring.compiler.marker_position_fields import (
    _marker_add_fields,
    _marker_rebalance_fields,
    _marker_reduce_fields,
)
from sis.research.strategy_lab.authoring.compiler.marker_signal_base import (
    _marker_signal_base,
)
from sis.research.strategy_lab.authoring.compiler.marker_state_rows import (
    _close_signal_row as _close_signal_row,
    _hold_signal_row as _hold_signal_row,
)
from sis.research.strategy_lab.authoring.contracts.spec import StrategyAuthoringSpec
from sis.research.strategy_lab.specs import SymbolBinding


def _reduce_signal_row(
    *,
    spec: StrategyAuthoringSpec,
    row: dict[str, Any],
    binding: SymbolBinding,
    generated_at: datetime,
) -> dict[str, Any]:
    return {
        **_marker_signal_base(
            spec=spec,
            row=row,
            binding=binding,
            generated_at=generated_at,
            side="reduce",
        ),
        **_marker_trade_control_defaults(),
        **_marker_reduce_fields(row=row, spec=spec),
        "reason_codes": [spec.rules.reduce_reason_code],
        "block_reasons": [],
    }


def _add_signal_row(
    *,
    spec: StrategyAuthoringSpec,
    row: dict[str, Any],
    binding: SymbolBinding,
    generated_at: datetime,
) -> dict[str, Any]:
    return {
        **_marker_signal_base(
            spec=spec,
            row=row,
            binding=binding,
            generated_at=generated_at,
            side="add",
        ),
        **_marker_trade_control_defaults(),
        **_marker_add_fields(row=row, spec=spec),
        "reason_codes": [spec.rules.add_reason_code],
        "block_reasons": [],
    }


def _rebalance_signal_row(
    *,
    spec: StrategyAuthoringSpec,
    row: dict[str, Any],
    binding: SymbolBinding,
    generated_at: datetime,
) -> dict[str, Any]:
    return {
        **_marker_signal_base(
            spec=spec,
            row=row,
            binding=binding,
            generated_at=generated_at,
            side="rebalance",
        ),
        **_marker_trade_control_defaults(),
        **_marker_rebalance_fields(row=row, spec=spec),
        "reason_codes": [spec.rules.rebalance_reason_code],
        "block_reasons": [],
    }
