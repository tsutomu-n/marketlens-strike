from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, cast

from sis.research.strategy_lab.authoring.compiler.common import _float_or_default
from sis.research.strategy_lab.authoring.contracts.spec import StrategyAuthoringSpec
from sis.venues.ids import VenueId


@dataclass(frozen=True)
class _PaperPreviewCandidateFields:
    execution_venue: VenueId
    execution_symbol: str
    real_market_symbol: str
    side: Literal["long", "short", "none"]
    timeframe: str
    raw_score: Any
    rank_score: Any
    percentile_rank: Any
    tail_bucket: Literal["top", "middle", "bottom", "none"]
    confidence: float
    entry_reason_codes: list[Any]
    position_weight: Any
    notional_usd: Any
    feature_snapshot_ref: Any
    quote_ref: Any
    tracking_ref: Any


def _paper_preview_candidate_fields(
    *, spec: StrategyAuthoringSpec, row: dict[str, Any], selected: bool
) -> _PaperPreviewCandidateFields:
    binding = spec.experiment.symbol_bindings[0]
    row_selected = selected and bool(row)
    return _PaperPreviewCandidateFields(
        execution_venue=cast(
            VenueId, row.get("execution_venue") if row else binding.execution_venue
        ),
        execution_symbol=str(row.get("execution_symbol") or binding.execution_symbol),
        real_market_symbol=str(row.get("real_market_symbol") or binding.real_market_symbol),
        side=cast(Literal["long", "short", "none"], row.get("side") if row_selected else "none"),
        timeframe=str(row.get("timeframe") or spec.rules.timeframe),
        raw_score=row.get("raw_score") if row else None,
        rank_score=row.get("rank_score") if row_selected else None,
        percentile_rank=row.get("percentile_rank") if row_selected else None,
        tail_bucket=cast(
            Literal["top", "middle", "bottom", "none"],
            row.get("tail_bucket") if row_selected else "none",
        ),
        confidence=_float_or_default(row.get("confidence") if row_selected else None, 0.0),
        entry_reason_codes=list(row.get("reason_codes") or []) if row_selected else [],
        position_weight=row.get("position_weight") if row_selected else None,
        notional_usd=row.get("notional_usd") if row_selected else None,
        feature_snapshot_ref=row.get("feature_snapshot_ref") if row else None,
        quote_ref=row.get("quote_ref") if row else None,
        tracking_ref=row.get("tracking_ref") if row else None,
    )
