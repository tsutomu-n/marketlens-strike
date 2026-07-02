from __future__ import annotations

import pytest
from pydantic import ValidationError

from sis.edge_candidate_factory.models import (
    BacktestKillGate,
    EdgeCandidateBoundary,
    EdgeCandidateSearchLedgerRow,
    LLMAdversarialEvidenceReview,
    RiskActualCashHandoff,
    SmartCandidatePriorReport,
    TrialMultiplicityAccount,
    VirtualExecutionGate,
)

from .fixtures import (
    backtest_kill_gate_payload,
    copy_payload,
    edge_candidate_search_ledger_row_payload,
    llm_adversarial_evidence_review_payload,
    risk_actual_cash_handoff_payload,
    smart_candidate_prior_report_payload,
    trial_multiplicity_account_payload,
    virtual_execution_gate_payload,
)


def test_edge_candidate_artifact_models_accept_valid_payloads() -> None:
    assert SmartCandidatePriorReport.model_validate(smart_candidate_prior_report_payload())
    assert EdgeCandidateSearchLedgerRow.model_validate(edge_candidate_search_ledger_row_payload())
    assert TrialMultiplicityAccount.model_validate(trial_multiplicity_account_payload())
    assert BacktestKillGate.model_validate(backtest_kill_gate_payload())
    assert VirtualExecutionGate.model_validate(virtual_execution_gate_payload())
    assert RiskActualCashHandoff.model_validate(risk_actual_cash_handoff_payload())
    assert LLMAdversarialEvidenceReview.model_validate(llm_adversarial_evidence_review_payload())


def test_boundary_rejects_unsafe_true_flags() -> None:
    payload = safe = EdgeCandidateBoundary().model_dump(mode="json")
    assert payload == {
        "paper_execution_allowed": False,
        "live_allowed": False,
        "permits_live_order": False,
        "live_conversion_allowed": False,
        "wallet_used": False,
        "signing_used": False,
        "exchange_write_used": False,
        "production_exchange_write_allowed": False,
        "production_exchange_write_used": False,
        "live_order_submitted": False,
        "auto_promote": False,
    }

    unsafe = dict(safe)
    unsafe["permits_live_order"] = True
    with pytest.raises(ValidationError):
        EdgeCandidateBoundary.model_validate(unsafe)


def test_models_reject_extra_fields() -> None:
    payload = smart_candidate_prior_report_payload()
    payload["unexpected"] = "not allowed"

    with pytest.raises(ValidationError):
        SmartCandidatePriorReport.model_validate(payload)


def test_report_counts_must_match_candidate_cards() -> None:
    payload = smart_candidate_prior_report_payload()
    payload["candidate_count_total"] = 2

    with pytest.raises(ValidationError, match="candidate_count_total"):
        SmartCandidatePriorReport.model_validate(payload)


def test_rejected_candidate_requires_rejection_reason() -> None:
    payload = smart_candidate_prior_report_payload()
    card = payload["candidate_cards"][0]
    card["candidate_decision"] = "REJECTED"
    card["rejection_reason"] = None

    with pytest.raises(ValidationError, match="REJECTED requires rejection_reason"):
        SmartCandidatePriorReport.model_validate(payload)


def test_virtual_gate_rejects_fixture_exchange_write() -> None:
    payload = virtual_execution_gate_payload()
    payload["exchange_write_used"] = True

    with pytest.raises(ValidationError, match="exchange_write_used"):
        VirtualExecutionGate.model_validate(payload)


def test_actual_cash_handoff_ready_requires_actual_cash_rows_ref() -> None:
    payload = risk_actual_cash_handoff_payload()
    payload["risk_taker_review_input_status"] = "READY_WITH_ACTUAL_CASH_ROWS"
    payload["actual_cash_report_gate_input_status"] = "READY_WITH_ACTUAL_CASH_ROWS"

    with pytest.raises(ValidationError, match="actual_cash_rows_ref"):
        RiskActualCashHandoff.model_validate(payload)


def test_llm_hard_blocker_count_must_match_findings() -> None:
    payload = llm_adversarial_evidence_review_payload()
    payload["hard_blocker_count"] = 0

    with pytest.raises(ValidationError, match="hard_blocker_count"):
        LLMAdversarialEvidenceReview.model_validate(payload)


def test_multiplicity_counts_cannot_be_success_only() -> None:
    payload = copy_payload(trial_multiplicity_account_payload())
    payload["success_only_reporting"] = True

    with pytest.raises(ValidationError):
        TrialMultiplicityAccount.model_validate(payload)
