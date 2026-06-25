from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from sis.venues.suitability import venue_suitability_block_reasons


@dataclass(frozen=True)
class _PaperPreviewCandidateDecision:
    status: Literal["candidate", "blocked", "hold", "no_signal"]
    block_reasons: list[str]
    selected: bool


def _paper_preview_candidate_decision(
    *,
    selected: bool,
    base_status: Literal["candidate", "hold", "no_signal"],
    fields: Any,
    rejection_reasons: list[str],
) -> _PaperPreviewCandidateDecision:
    candidate_block_reasons = [] if selected else list(rejection_reasons)
    if selected:
        candidate_block_reasons.extend(
            venue_suitability_block_reasons(
                venue_id=str(fields.execution_venue),
                execution_symbol=fields.execution_symbol,
                real_market_symbol=fields.real_market_symbol,
                stage="paper_candidate",
            )
        )
        candidate_block_reasons = list(dict.fromkeys(candidate_block_reasons))
    status = "blocked" if selected and candidate_block_reasons else base_status
    return _PaperPreviewCandidateDecision(
        status=status,
        block_reasons=candidate_block_reasons,
        selected=selected and not candidate_block_reasons,
    )
