from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator
import pytest
from pydantic import ValidationError

from sis.strategy_review.operator_review import OperatorReviewDecision, OperatorStrategyReview


def _schema() -> dict:
    return json.loads(
        Path("schemas/operator_strategy_review.v1.schema.json").read_text(encoding="utf-8")
    )


def _valid_operator_review() -> dict:
    return {
        "schema_version": "operator_strategy_review.v1",
        "review_id": "ndx-smoke-001",
        "reviewed_at": "2026-06-16T09:00:00Z",
        "producer": {
            "tool": "sis",
            "command": "strategy-review-record",
            "schema_version": "operator_strategy_review.v1",
        },
        "reviewer": "operator-a",
        "decision": "PAPER_OBSERVATION_CANDIDATE",
        "rationale": "Review packet is complete and boundary checks are clean.",
        "required_actions": [],
        "live_allowed": False,
        "paper_execution_allowed": False,
        "source_review": {
            "manifest_path": "data/strategy_reviews/ndx-smoke-001/review_manifest.json",
            "review_manifest_sha256": "sha256:" + "a" * 64,
            "review_markdown_path": "data/strategy_reviews/ndx-smoke-001/review.md",
            "review_markdown_sha256": "sha256:" + "b" * 64,
            "review_status": "READY_FOR_HUMAN_REVIEW",
            "source_safety_status": "PASS",
            "pack_validation_status": "PASS",
            "lifecycle_review_status": "present",
            "missing_required_count": 0,
            "invalid_required_count": 0,
            "boundary_violation_count": 0,
            "unknown_boundary_count": 0,
        },
    }


def test_operator_review_schema_accepts_valid_payload() -> None:
    payload = _valid_operator_review()

    Draft202012Validator.check_schema(_schema())
    Draft202012Validator(_schema()).validate(payload)
    OperatorStrategyReview.model_validate(payload)


def test_operator_review_pydantic_dump_matches_tracked_schema() -> None:
    operator_review = OperatorStrategyReview.model_validate(_valid_operator_review())
    payload = operator_review.model_dump(mode="json", exclude_none=True)

    assert payload["reviewed_at"] == "2026-06-16T09:00:00Z"
    Draft202012Validator(_schema()).validate(payload)


def test_operator_review_decision_enum_matches_schema() -> None:
    schema_enum = set(_schema()["properties"]["decision"]["enum"])

    assert schema_enum == {decision.value for decision in OperatorReviewDecision}


@pytest.mark.parametrize("field_name", ["live_allowed", "paper_execution_allowed"])
def test_operator_review_rejects_true_permission_flags(field_name: str) -> None:
    payload = _valid_operator_review()
    payload[field_name] = True

    assert list(Draft202012Validator(_schema()).iter_errors(payload))
    with pytest.raises(ValidationError):
        OperatorStrategyReview.model_validate(payload)


def test_operator_review_rejects_bare_hash() -> None:
    payload = _valid_operator_review()
    payload["source_review"]["review_manifest_sha256"] = "a" * 64

    assert list(Draft202012Validator(_schema()).iter_errors(payload))
    with pytest.raises(ValidationError):
        OperatorStrategyReview.model_validate(payload)


def test_operator_review_rejects_extra_fields_and_empty_rationale() -> None:
    payload = _valid_operator_review()
    payload["extra"] = "nope"
    payload["rationale"] = " "

    assert list(Draft202012Validator(_schema()).iter_errors(payload))
    with pytest.raises(ValidationError):
        OperatorStrategyReview.model_validate(payload)


def test_operator_review_needs_fix_requires_actions() -> None:
    payload = _valid_operator_review()
    payload["decision"] = "NEEDS_FIX"
    payload["required_actions"] = []

    assert list(Draft202012Validator(_schema()).iter_errors(payload))
    with pytest.raises(ValidationError):
        OperatorStrategyReview.model_validate(payload)


def test_operator_review_candidate_requires_clean_source_review() -> None:
    payload = _valid_operator_review()
    payload["source_review"]["pack_validation_status"] = "FAIL"

    assert list(Draft202012Validator(_schema()).iter_errors(payload))
    with pytest.raises(ValidationError):
        OperatorStrategyReview.model_validate(payload)
