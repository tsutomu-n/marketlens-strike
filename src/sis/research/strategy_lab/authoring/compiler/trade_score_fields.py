from __future__ import annotations

from typing import Any

from sis.research.strategy_lab.authoring.compiler.signal_selection import _tail_bucket
from sis.research.strategy_lab.authoring.contracts.spec import StrategyAuthoringSpec


def _trade_score_fields(
    *,
    spec: StrategyAuthoringSpec,
    row: dict[str, Any],
    raw_score: float | None,
    rank: float | None,
) -> dict[str, Any]:
    return {
        "raw_score": raw_score,
        "rank_score": rank,
        "percentile_rank": rank,
        "tail_bucket": _tail_bucket(rank),
        "confidence": spec.rules.confidence,
        "source_confidence": row.get("source_confidence"),
        "venue_quality_score": row.get("venue_quality_score"),
        "feature_snapshot_ref": None,
        "quote_ref": None,
        "tracking_ref": None,
    }
