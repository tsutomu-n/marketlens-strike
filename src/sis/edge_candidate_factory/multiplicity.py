from __future__ import annotations

from datetime import datetime
from collections.abc import Sequence

from sis.edge_candidate_factory._contracts import AdjustmentStatus, CandidateDecision
from sis.edge_candidate_factory.models import (
    AdjustmentMethods,
    ArtifactRef,
    EdgeCandidateSearchLedgerRow,
    ProducerInfo,
    TrialMultiplicityAccount,
)


class MultiplicityAccountError(ValueError):
    pass


def build_trial_multiplicity_account(
    *,
    account_id: str,
    created_at: datetime,
    source_refs: Sequence[ArtifactRef],
    candidate_run_id: str,
    search_ledger_rows: Sequence[EdgeCandidateSearchLedgerRow],
    expected_trial_count: int | None = None,
    validation_peek_count: int = 0,
    rerank_count: int = 0,
    sealed_test_used_for_selection: bool = False,
    producer_command: str = "edge-candidate-factory-build",
    known_gaps: Sequence[str] | None = None,
) -> TrialMultiplicityAccount:
    rows = list(search_ledger_rows)
    if not rows:
        raise MultiplicityAccountError(
            "multiplicity account requires at least one search ledger row"
        )
    if expected_trial_count is not None and len(rows) < expected_trial_count:
        raise MultiplicityAccountError(
            "selected-only or omitted-trial ledger detected: "
            f"expected {expected_trial_count}, observed {len(rows)}"
        )
    if sealed_test_used_for_selection:
        raise MultiplicityAccountError("sealed_test_used_for_selection must be false")

    family_trial_counts: dict[str, int] = {}
    for row in rows:
        family_trial_counts[row.family] = family_trial_counts.get(row.family, 0) + 1

    generated_count = sum(
        1 for row in rows if row.candidate_decision is CandidateDecision.GENERATED
    )
    rejected_count = sum(1 for row in rows if row.candidate_decision is CandidateDecision.REJECTED)
    computed_gaps = [
        "effective trial count is not estimated in T5",
        f"candidate_count_total_used_as_conservative_upper_bound={len(rows)}",
        "candidate_count_shortlisted means generated candidate rows; no promotion implied",
        *(known_gaps or []),
    ]

    return TrialMultiplicityAccount(
        account_id=account_id,
        created_at=created_at,
        producer=ProducerInfo(command=producer_command),
        source_refs=list(source_refs),
        candidate_run_id=candidate_run_id,
        candidate_count_total=len(rows),
        candidate_count_shortlisted=generated_count,
        candidate_count_rejected=rejected_count,
        family_count=len(family_trial_counts),
        family_trial_counts=family_trial_counts,
        parameter_grid_hashes=sorted({row.parameter_hash for row in rows}),
        candidate_cluster_count=len({row.candidate_cluster_id for row in rows}),
        effective_trial_count_status=AdjustmentStatus.NOT_ESTIMABLE,
        effective_trial_count=None,
        validation_peek_count=validation_peek_count,
        rerank_count=rerank_count,
        sealed_test_used_for_selection=False,
        success_only_reporting=False,
        adjustment_methods=AdjustmentMethods(
            benjamini_hochberg_fdr=AdjustmentStatus.NOT_ESTIMABLE,
            benjamini_yekutieli_fdr=AdjustmentStatus.NOT_ESTIMABLE,
            pbo=AdjustmentStatus.NOT_ESTIMABLE,
            white_reality_check=AdjustmentStatus.NOT_ESTIMABLE,
            deflated_sharpe_ratio=AdjustmentStatus.NOT_ESTIMABLE,
        ),
        known_gaps=list(dict.fromkeys(computed_gaps)),
    )
