from __future__ import annotations

from typing import Any

from sis.research.strategy_lab.authoring.compiler.common import _block_trade_row
from sis.research.strategy_lab.authoring.compiler.reward_risk import _reward_risk_ratio
from sis.research.strategy_lab.authoring.contracts.spec import StrategyAuthoringSpec


def _apply_reward_risk_gate(row: dict[str, Any], spec: StrategyAuthoringSpec) -> dict[str, Any]:
    minimum = row.get("min_reward_risk_ratio")
    if minimum is None or row.get("side") not in {"long", "short"}:
        return row
    ratio = _reward_risk_ratio(row)
    row["min_reward_risk_ratio"] = minimum
    row["reward_risk_ratio"] = ratio
    if ratio is None:
        return _block_trade_row(row, spec=spec, block_reason="reward_risk_ratio_missing")
    if ratio < minimum:
        return _block_trade_row(row, spec=spec, block_reason="reward_risk_ratio_too_low")
    return row
