from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator
import pytest

from sis.edge_candidate_factory.models import (
    BacktestKillGate,
    EdgeCandidateSearchLedgerRow,
    LLMAdversarialEvidenceReview,
    RiskActualCashHandoff,
    SmartCandidatePriorReport,
    TrialMultiplicityAccount,
    VirtualExecutionGate,
)

from .fixtures import copy_payload, payloads_by_schema


REPO_ROOT = Path(__file__).resolve().parents[2]

MODEL_BY_SCHEMA = {
    "smart_candidate_prior_report.v1.schema.json": SmartCandidatePriorReport,
    "edge_candidate_search_ledger.v1.schema.json": EdgeCandidateSearchLedgerRow,
    "trial_multiplicity_account.v1.schema.json": TrialMultiplicityAccount,
    "backtest_kill_gate.v1.schema.json": BacktestKillGate,
    "virtual_execution_gate.v1.schema.json": VirtualExecutionGate,
    "edge_candidate_risk_actual_cash_handoff.v1.schema.json": RiskActualCashHandoff,
    "llm_adversarial_evidence_review.v1.schema.json": LLMAdversarialEvidenceReview,
}


def _schema(name: str) -> dict:
    return json.loads((REPO_ROOT / "schemas" / name).read_text(encoding="utf-8"))


@pytest.mark.parametrize("schema_name", sorted(payloads_by_schema()))
def test_edge_candidate_schemas_accept_fixture_payloads(schema_name: str) -> None:
    schema = _schema(schema_name)
    payload = payloads_by_schema()[schema_name]

    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(payload)

    model = MODEL_BY_SCHEMA[schema_name].model_validate(payload)
    dumped = model.model_dump(mode="json", exclude_none=True)
    Draft202012Validator(schema).validate(dumped)


@pytest.mark.parametrize("schema_name", sorted(payloads_by_schema()))
def test_edge_candidate_schemas_reject_extra_fields(schema_name: str) -> None:
    payload = copy_payload(payloads_by_schema()[schema_name])
    payload["unexpected"] = "not allowed"

    errors = list(Draft202012Validator(_schema(schema_name)).iter_errors(payload))

    assert errors


@pytest.mark.parametrize("schema_name", sorted(payloads_by_schema()))
def test_edge_candidate_schemas_reject_unsafe_boundary_true(schema_name: str) -> None:
    payload = copy_payload(payloads_by_schema()[schema_name])
    payload["boundary"]["permits_live_order"] = True

    errors = list(Draft202012Validator(_schema(schema_name)).iter_errors(payload))

    assert errors
