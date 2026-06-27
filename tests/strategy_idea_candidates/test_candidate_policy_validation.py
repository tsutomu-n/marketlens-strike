from __future__ import annotations

from datetime import timedelta

from sis.backtest.artifact_io import sha256_file
from sis.strategy_idea_candidates.generator import (
    CandidateFamilyId,
    StrategyIdeaCandidateGeneratorConfig,
    build_deterministic_candidate_set_from_input_evidence,
)
from sis.strategy_idea_candidates.models import StrategyIdeaCandidateSet
from sis.strategy_idea_candidates.policies import validate_split_and_leakage_policy
from sis.strategy_inputs.io import write_json_artifact
from sis.strategy_inputs.models import StrategyInputContract, StrategyInputContractValidation

from .fixtures import valid_input_contract_payload, valid_input_validation_payload


def _candidate_set(tmp_path) -> StrategyIdeaCandidateSet:
    source = tmp_path / "data/research/ndx/source/ohlcv.csv"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text("ts,close,volume\n2026-06-17T21:00:00Z,1,100\n", encoding="utf-8")
    validation_path = tmp_path / "data/strategy_inputs/ndx/strategy_input_contract_validation.json"
    validation_payload = valid_input_validation_payload()
    validation_payload["source_results"][0]["actual_sha256"] = sha256_file(source)
    validation_payload["source_results"][0]["declared_sha256"] = sha256_file(source)
    write_json_artifact(validation_path, validation_payload)

    return build_deterministic_candidate_set_from_input_evidence(
        contract=StrategyInputContract.model_validate(
            valid_input_contract_payload(sha256=sha256_file(source))
        ),
        validation=StrategyInputContractValidation.model_validate(validation_payload),
        validation_path=validation_path,
        config=StrategyIdeaCandidateGeneratorConfig(
            candidate_set_id="ndx-policy-candidates-001",
            family_ids=[CandidateFamilyId.TREND_MOMENTUM],
            candidate_cap=2,
            shortlist_count=1,
            label_window={
                "start": "2025-01-01T00:00:00Z",
                "end": "2025-12-31T00:00:00Z",
            },
            feature_observation_window={
                "start": "2024-01-01T00:00:00Z",
                "end": "2025-12-30T00:00:00Z",
            },
            train_window={
                "start": "2024-01-01T00:00:00Z",
                "end": "2024-12-31T00:00:00Z",
            },
            validation_window={
                "start": "2025-01-01T00:00:00Z",
                "end": "2025-12-31T00:00:00Z",
            },
            sealed_test_window={
                "start": "2026-01-01T00:00:00Z",
                "end": "2026-06-18T00:00:00Z",
            },
            generated_at="2026-06-18T12:50:00Z",
        ),
    )


def test_policy_validation_passes_generator_output(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = validate_split_and_leakage_policy(_candidate_set(tmp_path))

    assert result.passed is True
    assert result.failures == []


def test_policy_validation_rejects_sealed_test_overlap(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    candidate_set = _candidate_set(tmp_path).model_copy(deep=True)
    candidate_set.split_policy.sealed_test_window.start = (
        candidate_set.split_policy.validation_window.end
    )

    result = validate_split_and_leakage_policy(candidate_set)

    assert result.passed is False
    assert any("sealed_test_window.start" in failure for failure in result.failures)


def test_policy_validation_rejects_candidate_label_window_in_sealed_test(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    candidate_set = _candidate_set(tmp_path).model_copy(deep=True)
    candidate_set.candidate_inventory[
        0
    ].label_window.end = candidate_set.split_policy.sealed_test_window.end

    result = validate_split_and_leakage_policy(candidate_set)

    assert result.passed is False
    assert any("label_window.end" in failure for failure in result.failures)


def test_policy_validation_rejects_source_observed_after_available_at(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    candidate_set = _candidate_set(tmp_path).model_copy(deep=True)
    candidate_set.source_artifacts[0].max_observed_timestamp = candidate_set.source_artifacts[
        0
    ].available_at + timedelta(seconds=1)

    result = validate_split_and_leakage_policy(candidate_set)

    assert result.passed is False
    assert any("max_observed_timestamp" in failure for failure in result.failures)
