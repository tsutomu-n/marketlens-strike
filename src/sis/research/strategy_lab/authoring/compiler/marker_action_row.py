from __future__ import annotations

from datetime import datetime
from typing import Any

from sis.research.strategy_lab.authoring.compiler.marker_defaults import (
    _marker_trade_control_defaults,
)
from sis.research.strategy_lab.authoring.compiler.marker_signal_base import (
    _marker_signal_base,
)
from sis.research.strategy_lab.authoring.contracts.spec import StrategyAuthoringSpec
from sis.research.strategy_lab.specs import SymbolBinding


def _marker_action_signal_row(
    *,
    spec: StrategyAuthoringSpec,
    row: dict[str, Any],
    binding: SymbolBinding,
    generated_at: datetime,
    side: str,
    position_fields: dict[str, Any],
    reason_code: str,
) -> dict[str, Any]:
    return {
        **_marker_signal_base(
            spec=spec,
            row=row,
            binding=binding,
            generated_at=generated_at,
            side=side,
        ),
        **_marker_trade_control_defaults(),
        **position_fields,
        "reason_codes": [reason_code],
        "block_reasons": [],
    }
