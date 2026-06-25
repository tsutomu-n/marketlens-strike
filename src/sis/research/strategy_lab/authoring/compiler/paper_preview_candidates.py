from __future__ import annotations

from datetime import datetime
from typing import Any

from sis.research.strategy_lab.authoring.compiler.paper_preview_candidate_fields import (
    _paper_preview_candidate_fields,
)
from sis.research.strategy_lab.authoring.compiler.paper_preview_candidate_decision import (
    _paper_preview_candidate_decision,
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
from sis.research.strategy_lab.authoring.compiler.paper_preview_selected_rows import (
    _paper_preview_selected_rows as _paper_preview_selected_rows,
)
from sis.research.strategy_lab.authoring.contracts.spec import StrategyAuthoringSpec
from sis.research.strategy_lab.candidates import TradeCandidate


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
        base_status = "candidate" if selected else ("no_signal" if not row else "hold")
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
        candidates.append(candidate)
        (selected_candidate_ids if decision.selected else rejected_candidate_ids).append(
            candidate_id
        )
    return candidates, selected_candidate_ids, rejected_candidate_ids
