from __future__ import annotations

import pytest

from sis.strategy_idea_candidates.models import StrategyIdeaCandidateSet
from sis.strategy_idea_candidates.operator_review import (
    StrategyIdeaCandidateOperatorReviewOutputExistsError,
    render_strategy_idea_candidate_operator_review_markdown,
    write_strategy_idea_candidate_operator_review,
)
from sis.strategy_idea_candidates.policies import validate_split_and_leakage_policy

from .fixtures import valid_candidate_set_payload


def _candidate_set() -> StrategyIdeaCandidateSet:
    return StrategyIdeaCandidateSet.model_validate(valid_candidate_set_payload())


def test_operator_review_markdown_includes_exploration_and_boundaries() -> None:
    candidate_set = _candidate_set()
    text = render_strategy_idea_candidate_operator_review_markdown(
        candidate_set,
        policy_validation=validate_split_and_leakage_policy(candidate_set),
    )

    assert "candidate_count_total: `2`" in text
    assert "candidate_count_shortlisted: `1`" in text
    assert "candidate_count_rejected: `1`" in text
    assert "duplicate_rejection_count: `1`" in text
    assert "policy_validation: `PASS`" in text
    assert "selection_adjusted_metrics_status" in text
    assert "NOT_IMPLEMENTED" in text
    assert "selection-adjusted metrics are not implemented" in text
    assert "duplicate parameterization rejected before shortlist" in text
    assert "alpha proof" in text
    assert "profit proof" in text
    assert "paper / live approval" in text


def test_operator_review_writer_is_deterministic(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    candidate_set = _candidate_set()
    first = write_strategy_idea_candidate_operator_review(
        candidate_set=candidate_set,
        out_dir=tmp_path / "data/strategy_idea_candidates/run-a/review",
    )
    second = write_strategy_idea_candidate_operator_review(
        candidate_set=candidate_set,
        out_dir=tmp_path / "data/strategy_idea_candidates/run-b/review",
    )

    assert first.report_path.read_text(encoding="utf-8") == second.report_path.read_text(
        encoding="utf-8"
    )


def test_operator_review_writer_refuses_existing_output(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    candidate_set = _candidate_set()
    out_dir = tmp_path / "data/strategy_idea_candidates/run-a/review"
    write_strategy_idea_candidate_operator_review(candidate_set=candidate_set, out_dir=out_dir)

    with pytest.raises(StrategyIdeaCandidateOperatorReviewOutputExistsError):
        write_strategy_idea_candidate_operator_review(candidate_set=candidate_set, out_dir=out_dir)
