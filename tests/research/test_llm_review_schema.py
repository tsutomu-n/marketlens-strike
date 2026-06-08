from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator
from pydantic import ValidationError

from sis.research.dag.review_contracts import LlmDagReview
from sis.research.dag.review_contracts import Layer22ExitDecision


FIXTURE_DIR = Path("tests/fixtures/research_layer_2_2/reviews")


def _review_payload(name: str) -> dict[str, Any]:
    text = (FIXTURE_DIR / name).read_text(encoding="utf-8")
    text = text.replace(
        "sha256:PACK_HASH_PLACEHOLDER",
        "sha256:1111111111111111111111111111111111111111111111111111111111111111",
    )
    return json.loads(text)


def test_llm_review_contract_accepts_valid_fixture_and_schema_file_exists() -> None:
    review = LlmDagReview.model_validate(_review_payload("valid_approve.json"))
    schema = json.loads(Path("schemas/llm_dag_review.v1.schema.json").read_text())

    assert review.schema_version == "llm_dag_review.v1"
    assert review.severity_counts.INFO == 1
    assert schema["title"] == "LLM DAG Review v1"
    Draft202012Validator(schema).validate(_review_payload("valid_approve.json"))


def test_layer22_review_schema_files_are_valid_json_schema() -> None:
    for path in [
        Path("schemas/llm_dag_review.v1.schema.json"),
        Path("schemas/layer_2_2_human_resolutions.v1.schema.json"),
        Path("schemas/layer_2_2_exit_decision.v1.schema.json"),
        Path("schemas/layer_2_2_freeze_manifest.v1.schema.json"),
    ]:
        Draft202012Validator.check_schema(json.loads(path.read_text()))


def test_exit_decision_contract_rejects_approve_with_second_review_required() -> None:
    payload = {
        "schema_version": "layer_2_2_exit_decision.v1",
        "dag_id": "HYP-NDX-001",
        "decision": "APPROVE_2_3",
        "pack_hash": "sha256:1111111111111111111111111111111111111111111111111111111111111111",
        "review_ids": ["review.fixture.approve"],
        "unresolved_human_decisions": [],
        "blocker_count": 0,
        "high_count": 0,
        "second_review_required": True,
        "created_at": "2026-06-08T10:00:00+00:00",
    }

    with pytest.raises(ValidationError, match="second_review_required=false"):
        Layer22ExitDecision.model_validate(payload)

    schema = json.loads(Path("schemas/layer_2_2_exit_decision.v1.schema.json").read_text())
    errors = list(Draft202012Validator(schema).iter_errors(payload))

    assert errors


def test_llm_review_contract_rejects_extra_property() -> None:
    payload = _review_payload("valid_approve.json")
    payload["unexpected"] = "nope"

    with pytest.raises(ValidationError):
        LlmDagReview.model_validate(payload)


def test_llm_review_contract_rejects_invalid_severity() -> None:
    payload = _review_payload("valid_approve.json")
    payload["findings"][0]["severity"] = "CRITICAL"

    with pytest.raises(ValidationError):
        LlmDagReview.model_validate(payload)


def test_llm_review_contract_rejects_missing_pack_hash() -> None:
    payload = _review_payload("valid_approve.json")
    del payload["pack_hash"]

    with pytest.raises(ValidationError):
        LlmDagReview.model_validate(payload)


def test_llm_review_contract_rejects_malformed_evidence_ref() -> None:
    payload = _review_payload("valid_approve.json")
    payload["findings"][0]["evidence_refs"] = ["NODE.open_gap_residual"]

    with pytest.raises(ValidationError):
        LlmDagReview.model_validate(payload)
