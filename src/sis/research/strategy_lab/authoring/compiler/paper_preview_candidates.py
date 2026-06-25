from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, cast

import polars as pl

from sis.research.strategy_lab.authoring.compiler.common import _float_or_default
from sis.research.strategy_lab.authoring.compiler.paper_preview_execution_fields import (
    _paper_preview_execution_fields,
)
from sis.research.strategy_lab.authoring.compiler.paper_preview_exit_fields import (
    _paper_preview_exit_fields,
)
from sis.research.strategy_lab.authoring.compiler.paper_preview_order_fields import (
    _paper_preview_order_fields,
)
from sis.research.strategy_lab.authoring.contracts.spec import StrategyAuthoringSpec
from sis.research.strategy_lab.candidates import TradeCandidate
from sis.venues.ids import VenueId
from sis.venues.suitability import venue_suitability_block_reasons


def _paper_preview_selected_rows(frame: pl.DataFrame) -> list[dict[str, Any]]:
    return [
        row
        for row in frame.sort(["ts_signal", "signal_id"]).to_dicts()
        if str(row.get("side") or "").lower() in {"long", "short"}
        and not list(row.get("block_reasons") or [])
    ][:1]


def _paper_preview_candidates(
    *,
    spec: StrategyAuthoringSpec,
    selected_rows: list[dict[str, Any]],
    selected: bool,
    trial_id: str,
    now: datetime,
    rejection_reasons: list[str],
) -> tuple[list[TradeCandidate], list[str], list[str]]:
    candidates: list[TradeCandidate] = []
    selected_candidate_ids: list[str] = []
    rejected_candidate_ids: list[str] = []
    rows_for_candidates = selected_rows if selected_rows else [{}]
    for row in rows_for_candidates:
        candidate_id = (
            f"candidate-{trial_id}-{row['signal_id']}" if row else f"candidate-{trial_id}-no-signal"
        )
        status = "candidate" if selected else ("no_signal" if not row else "hold")
        binding = spec.experiment.symbol_bindings[0]
        execution_venue = cast(
            VenueId, row.get("execution_venue") if row else binding.execution_venue
        )
        side = cast(
            Literal["long", "short", "none"], row.get("side") if selected and row else "none"
        )
        tail_bucket = cast(
            Literal["top", "middle", "bottom", "none"],
            row.get("tail_bucket") if selected and row else "none",
        )
        confidence = _float_or_default(row.get("confidence") if selected and row else None, 0.0)
        candidate_block_reasons = [] if selected else list(rejection_reasons)
        if selected:
            candidate_block_reasons.extend(
                venue_suitability_block_reasons(
                    venue_id=str(execution_venue),
                    execution_symbol=str(row.get("execution_symbol") or binding.execution_symbol),
                    real_market_symbol=str(
                        row.get("real_market_symbol") or binding.real_market_symbol
                    ),
                    stage="paper_candidate",
                )
            )
            candidate_block_reasons = list(dict.fromkeys(candidate_block_reasons))
        candidate_selected = selected and not candidate_block_reasons
        if selected and candidate_block_reasons:
            status = "blocked"
        candidate = TradeCandidate(
            schema_version="trade_candidate.v1",
            candidate_id=candidate_id,
            generated_at=now,
            signal_id=str(row.get("signal_id")) if row else None,
            strategy_id=spec.experiment.strategy_id,
            trial_id=trial_id,
            execution_venue=execution_venue,
            execution_symbol=str(row.get("execution_symbol") or binding.execution_symbol),
            real_market_symbol=str(row.get("real_market_symbol") or binding.real_market_symbol),
            side=side,
            timeframe=str(row.get("timeframe") or spec.rules.timeframe),
            status=status,
            raw_score=row.get("raw_score") if row else None,
            rank_score=row.get("rank_score") if selected and row else None,
            percentile_rank=row.get("percentile_rank") if selected and row else None,
            tail_bucket=tail_bucket,
            confidence=confidence,
            entry_reason_codes=list(row.get("reason_codes") or []) if selected and row else [],
            block_reasons=candidate_block_reasons,
            **_paper_preview_exit_fields(row=row, selected=selected),
            **_paper_preview_order_fields(row=row, selected=selected),
            **_paper_preview_execution_fields(row=row, selected=selected),
            position_weight=row.get("position_weight") if selected and row else None,
            notional_usd=row.get("notional_usd") if selected and row else None,
            feature_snapshot_ref=row.get("feature_snapshot_ref") if row else None,
            quote_ref=row.get("quote_ref") if row else None,
            tracking_ref=row.get("tracking_ref") if row else None,
        )
        candidates.append(candidate)
        (selected_candidate_ids if candidate_selected else rejected_candidate_ids).append(
            candidate_id
        )
    return candidates, selected_candidate_ids, rejected_candidate_ids
