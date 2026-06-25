from __future__ import annotations

from typing import Any

from sis.research.strategy_lab.authoring.compiler.signal_ids import _compiled_signal_id
from sis.research.strategy_lab.authoring.compiler.trade_block_neutral_fields import (
    _blocked_trade_neutral_fields,
)
from sis.research.strategy_lab.authoring.contracts.spec import StrategyAuthoringSpec


def _block_trade_row(
    row: dict[str, Any],
    *,
    spec: StrategyAuthoringSpec,
    block_reason: str,
) -> dict[str, Any]:
    blocked = dict(row)
    blocked["side"] = "none"
    blocked["signal_id"] = _compiled_signal_id(spec, blocked, side="none")
    blocked["confidence"] = 0.0
    blocked.update(_blocked_trade_neutral_fields(row))
    blocked["reason_codes"] = [spec.rules.hold_reason_code]
    blocked["block_reasons"] = [*list(row.get("block_reasons") or []), block_reason]
    return blocked
