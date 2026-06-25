from __future__ import annotations

from datetime import datetime
from typing import Any

from sis.research.strategy_lab.authoring.compiler.signal_ids import _signal_id
from sis.research.strategy_lab.authoring.contracts.base import _stable_digest
from sis.research.strategy_lab.authoring.contracts.spec import StrategyAuthoringSpec
from sis.research.strategy_lab.specs import SymbolBinding


def _marker_signal_base(
    *,
    spec: StrategyAuthoringSpec,
    row: dict[str, Any],
    binding: SymbolBinding,
    generated_at: datetime,
    side: str,
) -> dict[str, Any]:
    return {
        "schema_version": "strategy_signal.v1",
        "signal_id": _signal_id(spec, row, binding, side=side),
        "generated_at": generated_at,
        "strategy_id": spec.experiment.strategy_id,
        "strategy_family": spec.experiment.strategy_family,
        "strategy_version": spec.experiment.strategy_version,
        "trial_id": None,
        "parameter_hash": _stable_digest(spec.model_dump(mode="json")),
        "ts_signal": row["ts"],
        "timeframe": spec.rules.timeframe,
        "execution_venue": binding.execution_venue,
        "execution_symbol": binding.execution_symbol,
        "real_market_symbol": binding.real_market_symbol,
        "side": side,
        "raw_score": None,
        "rank_score": None,
        "percentile_rank": None,
        "tail_bucket": "none",
        "confidence": 0.0,
        "source_confidence": row.get("source_confidence"),
        "venue_quality_score": row.get("venue_quality_score"),
        "feature_snapshot_ref": None,
        "quote_ref": None,
        "tracking_ref": None,
    }
