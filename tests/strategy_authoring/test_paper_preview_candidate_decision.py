from types import SimpleNamespace

from sis.research.strategy_lab.authoring.compiler.paper_preview_candidate_decision import (
    _paper_preview_candidate_decision,
)


def _fields(
    *,
    execution_venue: str = "trade_xyz",
    execution_symbol: str = "ABC100",
    real_market_symbol: str = "ABC",
):
    return SimpleNamespace(
        execution_venue=execution_venue,
        execution_symbol=execution_symbol,
        real_market_symbol=real_market_symbol,
    )


def test_paper_preview_candidate_decision_selects_clean_selected_candidate() -> None:
    decision = _paper_preview_candidate_decision(
        selected=True,
        base_status="candidate",
        fields=_fields(),
        rejection_reasons=["unused"],
    )

    assert decision.status == "candidate"
    assert decision.block_reasons == []
    assert decision.selected is True


def test_paper_preview_candidate_decision_blocks_venue_unsuitable_selected_candidate() -> None:
    decision = _paper_preview_candidate_decision(
        selected=True,
        base_status="candidate",
        fields=_fields(
            execution_venue="trade_xyz",
            execution_symbol="XYZ100",
            real_market_symbol="QQQ",
        ),
        rejection_reasons=["unused"],
    )

    assert decision.status == "blocked"
    assert decision.block_reasons == ["VENUE_REQUIRES_RESIDUAL_VALIDATION_AND_OPERATOR_PROMOTION"]
    assert decision.selected is False


def test_paper_preview_candidate_decision_deduplicates_selected_block_reasons() -> None:
    decision = _paper_preview_candidate_decision(
        selected=True,
        base_status="candidate",
        fields=_fields(
            execution_venue="trade_xyz",
            execution_symbol="XYZ100",
            real_market_symbol="XYZ100",
        ),
        rejection_reasons=["unused"],
    )

    assert decision.block_reasons == list(dict.fromkeys(decision.block_reasons))


def test_paper_preview_candidate_decision_copies_rejections_for_unselected_candidate() -> None:
    rejection_reasons = ["insufficient_trades_or_no_signal"]

    decision = _paper_preview_candidate_decision(
        selected=False,
        base_status="no_signal",
        fields=_fields(
            execution_venue="trade_xyz",
            execution_symbol="XYZ100",
            real_market_symbol="QQQ",
        ),
        rejection_reasons=rejection_reasons,
    )
    rejection_reasons.append("mutated")

    assert decision.status == "no_signal"
    assert decision.block_reasons == ["insufficient_trades_or_no_signal"]
    assert decision.selected is False
