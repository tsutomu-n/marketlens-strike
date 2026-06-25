from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sis.research.strategy_lab.authoring.compiler.paper_preview_candidate_decision import (
    _paper_preview_candidate_decision,
)
from sis.research.strategy_lab.authoring.compiler.paper_preview_candidate_fields import (
    _paper_preview_candidate_fields,
)
from sis.research.strategy_lab.authoring.compiler.paper_preview_candidate_identity import (
    _base_status,
    _candidate_id,
)
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


@dataclass(frozen=True)
class _PaperPreviewCandidateRow:
    candidate: TradeCandidate
    selected: bool


def _paper_preview_candidate_row(
    *,
    spec: StrategyAuthoringSpec,
    row: dict[str, Any],
    selected: bool,
    trial_id: str,
    now: datetime,
    rejection_reasons: list[str],
) -> _PaperPreviewCandidateRow:
    candidate_id = _candidate_id(trial_id=trial_id, row=row)
    base_status = _base_status(selected=selected, row=row)
    fields = _paper_preview_candidate_fields(spec=spec, row=row, selected=selected)
    decision = _paper_preview_candidate_decision(
        selected=selected,
        base_status=base_status,
        fields=fields,
        rejection_reasons=rejection_reasons,
    )
    candidate = TradeCandidate(
        schema_version="trade_candidate.v1",
        candidate_id=candidate_id,
        generated_at=now,
        signal_id=str(row.get("signal_id")) if row else None,
        strategy_id=spec.experiment.strategy_id,
        trial_id=trial_id,
        execution_venue=fields.execution_venue,
        execution_symbol=fields.execution_symbol,
        real_market_symbol=fields.real_market_symbol,
        side=fields.side,
        timeframe=fields.timeframe,
        status=decision.status,
        raw_score=fields.raw_score,
        rank_score=fields.rank_score,
        percentile_rank=fields.percentile_rank,
        tail_bucket=fields.tail_bucket,
        confidence=fields.confidence,
        entry_reason_codes=fields.entry_reason_codes,
        block_reasons=decision.block_reasons,
        **_paper_preview_exit_fields(row=row, selected=selected),
        **_paper_preview_order_fields(row=row, selected=selected),
        **_paper_preview_execution_fields(row=row, selected=selected),
        position_weight=fields.position_weight,
        notional_usd=fields.notional_usd,
        feature_snapshot_ref=fields.feature_snapshot_ref,
        quote_ref=fields.quote_ref,
        tracking_ref=fields.tracking_ref,
    )
    return _PaperPreviewCandidateRow(candidate=candidate, selected=decision.selected)
