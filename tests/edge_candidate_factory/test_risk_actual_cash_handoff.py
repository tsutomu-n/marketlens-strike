from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from pydantic import ValidationError

from sis.edge_candidate_factory.models import ArtifactRef, RiskActualCashHandoff
from sis.edge_candidate_factory.risk_actual_cash_handoff import (
    build_risk_actual_cash_handoff,
)

from .fixtures import HASH_A, artifact_ref


REPO_ROOT = Path(__file__).resolve().parents[2]
TS = datetime(2026, 7, 2, 11, 0, tzinfo=timezone.utc)


def _schema(name: str) -> dict:
    return json.loads((REPO_ROOT / "schemas" / name).read_text(encoding="utf-8"))


def _ref(ref_id: str, schema_version: str, path: str) -> ArtifactRef:
    return ArtifactRef.model_validate(artifact_ref(ref_id, schema_version, path, HASH_A))


def _handoff(actual_cash_rows_ref: ArtifactRef | None = None) -> RiskActualCashHandoff:
    return build_risk_actual_cash_handoff(
        handoff_id="risk-cash-handoff-001",
        created_at=TS,
        candidate_id="edge-cand-001",
        candidate_report_ref=_ref(
            "smart-prior-report",
            "smart_candidate_prior_report.v1",
            "data/edge_candidate_factory/run/smart_candidate_prior_report.json",
        ),
        search_ledger_ref=_ref(
            "search-ledger",
            "edge_candidate_search_ledger.v1",
            "data/edge_candidate_factory/run/edge_candidate_search_ledger.jsonl",
        ),
        multiplicity_account_ref=_ref(
            "multiplicity",
            "trial_multiplicity_account.v1",
            "data/edge_candidate_factory/run/trial_multiplicity_account.json",
        ),
        backtest_kill_gate_ref=_ref(
            "backtest-kill",
            "backtest_kill_gate.v1",
            "data/edge_candidate_factory/run/backtest_kill_gate/edge-cand-001.json",
        ),
        virtual_execution_gate_ref=_ref(
            "virtual-gate",
            "virtual_execution_gate.v1",
            "data/edge_candidate_factory/run/virtual_execution_gate/edge-cand-001.json",
        ),
        actual_cash_rows_ref=actual_cash_rows_ref,
    )


def test_handoff_blocks_without_actual_cash_rows() -> None:
    handoff = _handoff()

    assert handoff.risk_taker_review_input_status == "BLOCKED_NEEDS_ACTUAL_CASH_ROWS"
    assert handoff.actual_cash_report_gate_input_status == "BLOCKED_NEEDS_ACTUAL_CASH_ROWS"
    assert handoff.actual_cash_rows_required is True
    assert handoff.actual_cash_rows_ref is None
    assert handoff.virtual_or_backtest_used_as_actual_cash is False
    assert "actual cash rows are missing" in handoff.known_gaps
    Draft202012Validator(
        _schema("edge_candidate_risk_actual_cash_handoff.v1.schema.json")
    ).validate(handoff.model_dump(mode="json"))


def test_handoff_ready_requires_actual_cash_rows_ref() -> None:
    handoff = _handoff(
        _ref(
            "actual-cash-rows",
            "crypto_perp_tournament_rows.v2",
            "data/crypto_perp/actual_cash_rows/latest/actual_cash_rows.jsonl",
        )
    )

    assert handoff.risk_taker_review_input_status == "READY_WITH_ACTUAL_CASH_ROWS"
    assert handoff.actual_cash_report_gate_input_status == "READY_WITH_ACTUAL_CASH_ROWS"
    assert handoff.actual_cash_rows_ref is not None


def test_handoff_rejects_virtual_or_backtest_as_actual_cash() -> None:
    payload = _handoff().model_dump(mode="json")
    payload["virtual_or_backtest_used_as_actual_cash"] = True

    with pytest.raises(ValidationError):
        RiskActualCashHandoff.model_validate(payload)
