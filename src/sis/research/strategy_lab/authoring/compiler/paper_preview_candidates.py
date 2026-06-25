from __future__ import annotations

from datetime import datetime
from typing import Any

from sis.research.strategy_lab.authoring.compiler.paper_preview_candidate_row import (
    _paper_preview_candidate_row,
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
        result = _paper_preview_candidate_row(
            spec=spec,
            row=row,
            selected=selected,
            trial_id=trial_id,
            now=now,
            rejection_reasons=rejection_reasons,
        )
        candidate = result.candidate
        candidates.append(candidate)
        (selected_candidate_ids if result.selected else rejected_candidate_ids).append(
            candidate.candidate_id
        )
    return candidates, selected_candidate_ids, rejected_candidate_ids
