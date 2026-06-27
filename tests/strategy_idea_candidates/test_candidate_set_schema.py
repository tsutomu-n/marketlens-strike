from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator
import pytest
from pydantic import ValidationError

from sis.strategy_idea_candidates.models import CandidateSetStatus, StrategyIdeaCandidateSet

from .fixtures import copy_payload, valid_candidate_set_payload


REPO_ROOT = Path(__file__).resolve().parents[2]


def _schema() -> dict:
    return json.loads(
        (REPO_ROOT / "schemas/strategy_idea_candidate_set.v1.schema.json").read_text(
            encoding="utf-8"
        )
    )


def test_candidate_set_schema_accepts_valid_payload(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    payload = valid_candidate_set_payload()

    Draft202012Validator.check_schema(_schema())
    Draft202012Validator(_schema()).validate(payload)
    candidate_set = StrategyIdeaCandidateSet.model_validate(payload)

    assert candidate_set.candidate_set_status is CandidateSetStatus.BUILT
    assert candidate_set.search_ledger_summary.candidate_count_total == 2


def test_candidate_set_schema_requires_source_artifacts(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    payload = valid_candidate_set_payload()
    payload.pop("source_artifacts")

    assert list(Draft202012Validator(_schema()).iter_errors(payload))
    with pytest.raises(ValidationError):
        StrategyIdeaCandidateSet.model_validate(payload)


def test_candidate_set_schema_rejects_permission_flags(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    payload = valid_candidate_set_payload()
    payload["boundary"]["permits_paper_candidate"] = True
    payload["candidate_inventory"][0]["boundary"]["auto_promote"] = True

    assert list(Draft202012Validator(_schema()).iter_errors(payload))
    with pytest.raises(ValidationError):
        StrategyIdeaCandidateSet.model_validate(payload)


def test_candidate_set_schema_rejects_invalid_status(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    payload = valid_candidate_set_payload()
    payload["candidate_set_status"] = "READY_FOR_PAPER"

    assert list(Draft202012Validator(_schema()).iter_errors(payload))
    with pytest.raises(ValidationError):
        StrategyIdeaCandidateSet.model_validate(payload)


def test_candidate_set_schema_rejects_invalid_sha256(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    payload = valid_candidate_set_payload()
    payload["source_artifacts"][0]["sha256"] = "b" * 64

    assert list(Draft202012Validator(_schema()).iter_errors(payload))
    with pytest.raises(ValidationError):
        StrategyIdeaCandidateSet.model_validate(payload)


def test_candidate_decision_reason_matches_decision(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    payload = copy_payload(valid_candidate_set_payload())
    payload["candidate_inventory"][0].pop("shortlist_reason")

    with pytest.raises(ValidationError, match="SHORTLISTED requires shortlist_reason"):
        StrategyIdeaCandidateSet.model_validate(payload)
