from __future__ import annotations

import json
from datetime import datetime, timezone

from sis.research.strategy_lab.authoring.compiler.paper_preview_output_writers import (
    _write_paper_preview_candidate_pack,
    _write_paper_preview_promotion_decision,
)
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
        scorecard_summary={"schema_version": "strategy_scorecard.v1"},
        selected_rows=[],
        selected_signal_ids=[],
        selected=False,
    )


def _candidate(*, generated_at: datetime) -> TradeCandidate:
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


def test_write_paper_preview_candidate_pack_uses_canonical_path_and_json(
    tmp_path,
) -> None:
    spec = _spec(tmp_path)
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    pack = _paper_preview_candidate_pack(
        spec=spec,
        context=_context(),
        candidates=[_candidate(generated_at=now)],
        selected_candidate_ids=[],
        rejected_candidate_ids=["candidate-trial-run-1-no-signal"],
        rejection_reasons=["insufficient_trades_or_no_signal"],
        generated_at=now,
    )

    out = _write_paper_preview_candidate_pack(data_dir=tmp_path, pack=pack)

    assert out == tmp_path / "research/paper_candidate_pack.json"
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "paper_candidate_pack.v1"
    assert payload["pack_id"] == "paper-pack-run-1"
    assert payload["exchange_write_used"] is False


def test_write_paper_preview_promotion_decision_uses_canonical_path_and_json(
    tmp_path,
) -> None:
    spec = _spec(tmp_path)
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    context = _context()
    pack = _paper_preview_candidate_pack(
        spec=spec,
        context=context,
        candidates=[_candidate(generated_at=now)],
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

    out = _write_paper_preview_promotion_decision(data_dir=tmp_path, decision=decision)

    assert out == tmp_path / "research/promotion_decision.json"
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "promotion_decision.v1"
    assert payload["source_pack_id"] == "paper-pack-run-1"
    assert payload["exchange_write_used"] is False
