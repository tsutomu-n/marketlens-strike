from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator
import pytest
from pydantic import ValidationError

from sis.strategy_input_feedback.models import (
    StrategyInputContractUpdateProposal,
    StrategyInputContractUpdateReview,
)


REPO_ROOT = Path(__file__).resolve().parents[2]


def _proposal_schema() -> dict:
    return json.loads(
        (REPO_ROOT / "schemas/strategy_input_contract_update_proposal.v1.schema.json").read_text(
            encoding="utf-8"
        )
    )


def _review_schema() -> dict:
    return json.loads(
        (REPO_ROOT / "schemas/strategy_input_contract_update_review.v1.schema.json").read_text(
            encoding="utf-8"
        )
    )


def _proposal_payload() -> dict:
    return {
        "schema_version": "strategy_input_contract_update_proposal.v1",
        "proposal_id": "proposal-001",
        "strategy_id": "ndx-breakout-001",
        "created_at": "2026-06-22T09:00:00Z",
        "producer": {"tool": "sis", "command": "strategy-input-feedback-proposal-build"},
        "status": "READY_FOR_HUMAN_REVIEW",
        "source_artifacts": [
            {
                "artifact_kind": "strategy_input_contract",
                "path": "data/strategy_inputs/contract.json",
                "sha256": "sha256:" + "a" * 64,
                "schema_version": "strategy_input_contract.v1",
            },
            {
                "artifact_kind": "runtime_observation",
                "path": "data/runtime/observation.json",
                "sha256": "sha256:" + "b" * 64,
                "schema_version": "strategy_runtime_observation_manifest.v1",
            },
        ],
        "proposed_changes": [
            {
                "change_id": "change-001",
                "target_section": "execution_reality",
                "recommendation": "Review runtime no-fill evidence before editing the contract.",
                "evidence_summary": "Runtime observation found no-fill behavior.",
                "source_reason": "runtime_observation:INGESTED",
                "requires_human_review": True,
            }
        ],
        "blocked_reasons": [],
        "requires_human_review": True,
        "auto_applied": False,
        "direct_contract_edit_allowed": False,
        "paper_execution_allowed": False,
        "live_allowed": False,
        "boundary": {
            "permits_live_order": False,
            "live_conversion_allowed": False,
            "wallet_used": False,
            "signing_used": False,
            "exchange_write_used": False,
        },
        "feedback_boundary": {
            "permits_live_order": False,
            "live_conversion_allowed": False,
            "permits_wallet": False,
            "permits_signing": False,
            "permits_exchange_write": False,
            "wallet_used": False,
            "signing_used": False,
            "exchange_write_used": False,
            "paper_execution_allowed": False,
            "live_allowed": False,
            "auto_applied": False,
            "direct_contract_edit_allowed": False,
        },
    }


def _review_payload() -> dict:
    return {
        "schema_version": "strategy_input_contract_update_review.v1",
        "review_id": "review-001",
        "proposal_id": "proposal-001",
        "strategy_id": "ndx-breakout-001",
        "reviewed_at": "2026-06-22T09:15:00Z",
        "producer": {"tool": "sis", "command": "strategy-input-feedback-proposal-review"},
        "reviewer": "operator-a",
        "decision": "APPROVE_FOR_MANUAL_CONTRACT_UPDATE",
        "rationale": "Approved as input to manual contract update only.",
        "approved_change_ids": ["change-001"],
        "required_actions": [],
        "source_proposal": {
            "proposal_path": "data/strategy_input_feedback/proposal-001.json",
            "proposal_sha256": "sha256:" + "c" * 64,
            "proposal_id": "proposal-001",
            "proposal_status": "READY_FOR_HUMAN_REVIEW",
            "proposed_change_ids": ["change-001"],
            "proposed_change_count": 1,
            "auto_applied": False,
            "direct_contract_edit_allowed": False,
            "paper_execution_allowed": False,
            "live_allowed": False,
        },
        "manual_contract_update_input_allowed": True,
        "requires_human_contract_update": True,
        "auto_applied": False,
        "direct_contract_edit_allowed": False,
        "paper_execution_allowed": False,
        "live_allowed": False,
        "boundary": {
            "permits_live_order": False,
            "live_conversion_allowed": False,
            "wallet_used": False,
            "signing_used": False,
            "exchange_write_used": False,
        },
        "feedback_boundary": {
            "permits_live_order": False,
            "live_conversion_allowed": False,
            "permits_wallet": False,
            "permits_signing": False,
            "permits_exchange_write": False,
            "wallet_used": False,
            "signing_used": False,
            "exchange_write_used": False,
            "paper_execution_allowed": False,
            "live_allowed": False,
            "auto_applied": False,
            "direct_contract_edit_allowed": False,
        },
    }


def test_proposal_schema_and_model_accept_valid_payload() -> None:
    payload = _proposal_payload()

    Draft202012Validator.check_schema(_proposal_schema())
    Draft202012Validator(_proposal_schema()).validate(payload)
    model = StrategyInputContractUpdateProposal.model_validate(payload)
    dumped = model.model_dump(mode="json", exclude_none=True)
    Draft202012Validator(_proposal_schema()).validate(dumped)


def test_review_schema_and_model_accept_valid_payload() -> None:
    payload = _review_payload()

    Draft202012Validator.check_schema(_review_schema())
    Draft202012Validator(_review_schema()).validate(payload)
    model = StrategyInputContractUpdateReview.model_validate(payload)
    dumped = model.model_dump(mode="json", exclude_none=True)
    Draft202012Validator(_review_schema()).validate(dumped)


@pytest.mark.parametrize(
    ("field_path", "value"),
    [
        (("schema_version",), "strategy_input_contract_update_proposal.v2"),
        (("boundary", "wallet_used"), True),
        (("feedback_boundary", "direct_contract_edit_allowed"), True),
        (("source_artifacts", 0, "path"), "/abs/contract.json"),
    ],
)
def test_proposal_rejects_unsafe_shape(field_path: tuple, value: object) -> None:
    payload = _proposal_payload()
    target = payload
    for key in field_path[:-1]:
        target = target[key]
    target[field_path[-1]] = value

    assert list(Draft202012Validator(_proposal_schema()).iter_errors(payload))
    with pytest.raises(ValidationError):
        StrategyInputContractUpdateProposal.model_validate(payload)


def test_proposal_without_source_contract_is_not_ready() -> None:
    payload = _proposal_payload()
    payload["status"] = "READY_FOR_HUMAN_REVIEW"
    payload["source_artifacts"] = [
        source
        for source in payload["source_artifacts"]
        if source["artifact_kind"] != "strategy_input_contract"
    ]

    with pytest.raises(ValidationError, match="source contract context"):
        StrategyInputContractUpdateProposal.model_validate(payload)

    payload["status"] = "NEEDS_SOURCE_CONTRACT_CONTEXT"
    StrategyInputContractUpdateProposal.model_validate(payload)


def test_review_rejects_unknown_approved_change_id() -> None:
    payload = _review_payload()
    payload["approved_change_ids"] = ["missing-change"]

    with pytest.raises(ValidationError, match="approved_change_ids not found"):
        StrategyInputContractUpdateReview.model_validate(payload)


def test_review_rejects_needs_fix_without_actions_and_reject_with_approved_ids() -> None:
    needs_fix = _review_payload()
    needs_fix["decision"] = "NEEDS_FIX"
    needs_fix["approved_change_ids"] = []
    needs_fix["manual_contract_update_input_allowed"] = False
    with pytest.raises(ValidationError, match="NEEDS_FIX requires"):
        StrategyInputContractUpdateReview.model_validate(needs_fix)

    rejected = _review_payload()
    rejected["decision"] = "REJECT"
    rejected["manual_contract_update_input_allowed"] = False
    with pytest.raises(ValidationError, match="REJECT/HOLD"):
        StrategyInputContractUpdateReview.model_validate(rejected)
