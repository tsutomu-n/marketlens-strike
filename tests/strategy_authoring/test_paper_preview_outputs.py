from __future__ import annotations

from datetime import datetime, timezone

from sis.research.strategy_lab.authoring.compiler.paper_preview_outputs import (
    _paper_preview_candidate_pack,
    _paper_preview_promotion_decision,
)
from sis.research.strategy_lab.authoring.compiler.paper_preview_run_context import (
    _PaperPreviewRunContext,
)
from sis.research.strategy_lab.candidates import TradeCandidate

from .helpers import _write_spec, load_authoring_spec


def _spec(tmp_path):
    spec_path = tmp_path / "spec.yaml"
    _write_spec(spec_path)
    return load_authoring_spec(spec_path)


def _context() -> _PaperPreviewRunContext:
    return _PaperPreviewRunContext(
        parameter_hash="param-hash",
        run_id="run-1",
        trial_id="trial-run-1",
        trial_group_id="trial-group-run-1",
        scorecard_summary={"total_return": -0.01},
        selected_rows=[],
        selected_signal_ids=[],
        selected=False,
    )


def _no_signal_candidate(*, generated_at: datetime) -> TradeCandidate:
    return TradeCandidate(
        schema_version="trade_candidate.v1",
        candidate_id="candidate-trial-run-1-no-signal",
        generated_at=generated_at,
        signal_id=None,
        strategy_id="trend_pullback_user_v1",
        trial_id="trial-run-1",
        execution_venue="trade_xyz",
        execution_symbol="XYZ100",
        real_market_symbol="QQQ",
        side="none",
        timeframe="4h",
        status="no_signal",
        raw_score=None,
        rank_score=None,
        percentile_rank=None,
        tail_bucket="none",
        confidence=0.0,
        block_reasons=["insufficient_trades_or_no_signal"],
        feature_snapshot_ref=None,
        quote_ref=None,
        tracking_ref=None,
    )


def test_paper_preview_candidate_pack_builder_preserves_fixed_metadata(tmp_path) -> None:
    spec = _spec(tmp_path)
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    candidate = _no_signal_candidate(generated_at=now)

    pack = _paper_preview_candidate_pack(
        spec=spec,
        context=_context(),
        candidates=[candidate],
        selected_candidate_ids=[],
        rejected_candidate_ids=[candidate.candidate_id],
        rejection_reasons=["insufficient_trades_or_no_signal"],
        generated_at=now,
    )

    assert pack.schema_version == "paper_candidate_pack.v1"
    assert pack.pack_id == "paper-pack-run-1"
    assert pack.generated_at == now
    assert pack.evaluation_plan_id == "strategy_authoring_v1"
    assert pack.data_snapshot_id == "data-snap-current"
    assert pack.feature_snapshot_id == "feature-snap-current"
    assert pack.trial_group_id == "trial-group-run-1"
    assert pack.candidates == [candidate]
    assert pack.selected_candidate_ids == []
    assert pack.rejected_candidate_ids == [candidate.candidate_id]
    assert pack.selection_policy == {
        "source": "strategy_authoring",
        "default_decision": "hold",
    }
    assert pack.reason_codes == ["strategy_authoring_v1"]
    assert pack.block_reasons == ["insufficient_trades_or_no_signal"]
    assert pack.paper_ready_claimed is False
    assert pack.live_ready_claimed is False
    assert pack.wallet_used is False
    assert pack.exchange_write_used is False


def test_paper_preview_promotion_decision_builder_preserves_safety_boundary(tmp_path) -> None:
    spec = _spec(tmp_path)
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    context = _context()
    pack = _paper_preview_candidate_pack(
        spec=spec,
        context=context,
        candidates=[_no_signal_candidate(generated_at=now)],
        selected_candidate_ids=[],
        rejected_candidate_ids=["candidate-trial-run-1-no-signal"],
        rejection_reasons=["insufficient_trades_or_no_signal"],
        generated_at=now,
    )

    decision = _paper_preview_promotion_decision(
        spec=spec,
        context=context,
        pack=pack,
        generated_at=now,
    )

    assert decision.schema_version == "promotion_decision.v1"
    assert decision.promotion_id == "promotion-run-1"
    assert decision.generated_at == now
    assert decision.source_pack_id == "paper-pack-run-1"
    assert decision.reviewer is None
    assert decision.from_stage == "strategy_lab"
    assert decision.to_stage == "paper_observation"
    assert decision.decision == "hold"
    assert decision.required_evidence == [
        "trial_ledger",
        "paper_candidate_pack",
        "strategy_scorecard",
    ]
    assert decision.observed_evidence == [
        "trial_ledger",
        "paper_candidate_pack",
        "strategy_scorecard",
    ]
    assert decision.approval_reasons == []
    assert decision.rejection_reasons == ["operator_review_required"]
    assert decision.scorecard_summary == {"total_return": -0.01}
    assert decision.paper_ready_claimed is False
    assert decision.live_ready_claimed is False
    assert decision.wallet_used is False
    assert decision.exchange_write_used is False
