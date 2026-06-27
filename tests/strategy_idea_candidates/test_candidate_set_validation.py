from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from sis.backtest.artifact_io import sha256_file
from sis.strategy_idea_candidates.models import CandidateSetStatus, StrategyIdeaCandidateSet
from sis.strategy_idea_candidates.service import build_blocked_candidate_set_from_input_evidence
from sis.strategy_inputs.models import StrategyInputContract, StrategyInputContractValidation
from sis.strategy_inputs.io import write_json_artifact

from .fixtures import (
    copy_payload,
    valid_candidate_set_payload,
    valid_input_contract_payload,
    valid_input_validation_payload,
)


def test_candidate_set_rejects_count_mismatch(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    payload = valid_candidate_set_payload()
    payload["search_ledger_summary"]["candidate_count_total"] = 3

    with pytest.raises(ValidationError, match="candidate_count_total"):
        StrategyIdeaCandidateSet.model_validate(payload)


def test_candidate_set_rejects_selected_rejected_id_overlap(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    payload = valid_candidate_set_payload()
    payload["selection_policy"]["rejected_candidate_ids"].append("idea-cand-001")

    with pytest.raises(ValidationError, match="must not overlap"):
        StrategyIdeaCandidateSet.model_validate(payload)


def test_candidate_set_rejects_unknown_selection_id(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    payload = valid_candidate_set_payload()
    payload["selection_policy"]["shortlisted_candidate_ids"] = ["missing-candidate"]

    with pytest.raises(ValidationError, match="unknown candidate id"):
        StrategyIdeaCandidateSet.model_validate(payload)


def test_candidate_set_rejects_success_only_inventory(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    payload = valid_candidate_set_payload()
    payload["candidate_inventory"] = [payload["candidate_inventory"][0]]
    payload["search_ledger_summary"]["candidate_count_total"] = 1
    payload["search_ledger_summary"]["candidate_count_shortlisted"] = 1
    payload["search_ledger_summary"]["candidate_count_rejected"] = 0
    payload["selection_policy"]["rejected_candidate_ids"] = []

    with pytest.raises(ValidationError, match="success-only"):
        StrategyIdeaCandidateSet.model_validate(payload)


def test_candidate_set_rejects_built_from_non_pass_input_validation(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    payload = valid_candidate_set_payload()
    payload["input_contract_validation_refs"][0]["validation_status"] = "NEEDS_FIX"

    with pytest.raises(ValidationError, match="BUILT requires PASS"):
        StrategyIdeaCandidateSet.model_validate(payload)


def test_blocked_candidate_set_from_non_pass_input_evidence(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    source = tmp_path / "data/research/ndx/source/ohlcv.csv"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text("ts,close\n2026-06-19T12:00:00Z,1\n", encoding="utf-8")
    contract_payload = valid_input_contract_payload(sha256=sha256_file(source))
    contract_payload["sources"][0]["available_at"] = "2026-06-18T00:05:00Z"
    validation_payload = valid_input_validation_payload()
    validation_payload["validation_status"] = "NEEDS_FIX"
    validation_payload["source_results"][0]["status"] = "invalid"
    validation_payload["source_results"][0]["hash_matches"] = False
    validation_path = tmp_path / "data/strategy_inputs/ndx/strategy_input_contract_validation.json"
    write_json_artifact(validation_path, validation_payload)

    candidate_set = build_blocked_candidate_set_from_input_evidence(
        candidate_set_id="blocked-ndx-candidate-set-001",
        contract=StrategyInputContract.model_validate(contract_payload),
        validation=StrategyInputContractValidation.model_validate(validation_payload),
        validation_path=validation_path,
        generated_at="2026-06-18T12:46:00Z",
        generator_version="fixture-0.1",
    )

    assert candidate_set.candidate_set_status is CandidateSetStatus.BLOCKED_INPUT_EVIDENCE
    assert candidate_set.candidate_inventory == []
    assert candidate_set.search_ledger_summary.candidate_count_total == 0
    assert candidate_set.input_contract_validation_refs[0].validation_status.value == "NEEDS_FIX"
    assert candidate_set.input_contract_validation_refs[0].validation_sha256 == sha256_file(
        validation_path
    )


def test_candidate_set_rejects_missing_source_summary(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    payload = valid_candidate_set_payload()
    payload["source_artifacts"] = []

    with pytest.raises(ValidationError, match="source_artifacts"):
        StrategyIdeaCandidateSet.model_validate(payload)
