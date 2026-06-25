from __future__ import annotations

from typing import Any

from sis.research.strategy_lab.authoring.contracts.base import _stable_digest
from sis.research.strategy_lab.authoring.contracts.spec import StrategyAuthoringSpec
from sis.research.strategy_lab.specs import SymbolBinding


def _compiled_signal_id(spec: StrategyAuthoringSpec, row: dict[str, Any], *, side: str) -> str:
    return _stable_digest(
        {
            "strategy_id": spec.experiment.strategy_id,
            "ts": row.get("ts_signal"),
            "execution_symbol": row.get("execution_symbol"),
            "side": side,
            "reason_code": spec.rules.reason_code,
        }
    )


def _signal_id(
    spec: StrategyAuthoringSpec,
    row: dict[str, Any],
    binding: SymbolBinding,
    *,
    side: str | None = None,
) -> str:
    return _stable_digest(
        {
            "strategy_id": spec.experiment.strategy_id,
            "ts": row.get("ts"),
            "execution_symbol": binding.execution_symbol,
            "side": side or spec.rules.side,
            "reason_code": spec.rules.reason_code,
        }
    )


def _multi_leg_group_id(
    spec: StrategyAuthoringSpec,
    row: dict[str, Any],
    *,
    base_side: str,
) -> str:
    return _stable_digest(
        {
            "strategy_id": spec.experiment.strategy_id,
            "ts": row.get("ts"),
            "canonical_symbol": row.get("canonical_symbol"),
            "anchor_real_market_symbol": spec.rules.multi_leg.anchor_real_market_symbol,
            "base_side": base_side,
            "reason_code": spec.rules.reason_code,
        }
    )
