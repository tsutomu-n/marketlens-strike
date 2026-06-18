from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator
import pytest
from pydantic import ValidationError

from sis.strategy_inputs.models import IdeaIntakeDecision, StrategyIntakeDecision


REPO_ROOT = Path(__file__).resolve().parents[2]


def _schema() -> dict:
    return json.loads(
        (REPO_ROOT / "schemas/strategy_intake_decision.v1.schema.json").read_text(encoding="utf-8")
    )


def valid_decision_payload() -> dict:
    return {
        "schema_version": "strategy_intake_decision.v1",
        "idea_id": "ndx-breakout-001",
        "decided_at": "2026-06-18T12:45:00Z",
        "producer": {"tool": "sis", "command": "strategy-intake-validate"},
        "decision": "READY_FOR_AUTHORING_DRAFT",
        "required_actions": [],
        "input_contract_refs": [
            {
                "contract_id": "ndx-breakout-inputs-001",
                "validation_status": "PASS",
            }
        ],
        "summary": {
            "missing_hypothesis": False,
            "missing_baseline": False,
            "missing_invalidation": False,
            "missing_risk": False,
            "missing_required_inputs": False,
            "boundary_violation_count": 0,
        },
        "boundary": {
            "permits_live_order": False,
            "live_conversion_allowed": False,
            "wallet_used": False,
            "signing_used": False,
            "exchange_write_used": False,
        },
    }


def test_intake_decision_schema_accepts_valid_payload(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    payload = valid_decision_payload()

    Draft202012Validator.check_schema(_schema())
    Draft202012Validator(_schema()).validate(payload)
    StrategyIntakeDecision.model_validate(payload)


def test_intake_decision_schema_rejects_ready_with_actions() -> None:
    payload = valid_decision_payload()
    payload["required_actions"] = ["Fix input contract"]

    assert list(Draft202012Validator(_schema()).iter_errors(payload))
    with pytest.raises(ValidationError):
        StrategyIntakeDecision.model_validate(payload)


def test_intake_decision_schema_rejects_permission_true() -> None:
    payload = valid_decision_payload()
    payload["boundary"]["exchange_write_used"] = True

    assert list(Draft202012Validator(_schema()).iter_errors(payload))
    with pytest.raises(ValidationError):
        StrategyIntakeDecision.model_validate(payload)


def test_intake_decision_enum_matches_schema() -> None:
    enum_values = set(_schema()["properties"]["decision"]["enum"])

    assert enum_values == {decision.value for decision in IdeaIntakeDecision}
