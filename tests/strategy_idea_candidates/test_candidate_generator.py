from __future__ import annotations

import json

import pytest

from sis.backtest.artifact_io import sha256_file
from sis.strategy_idea_candidates.generator import (
    CandidateFamilyId,
    StrategyIdeaCandidateGeneratorError,
    StrategyIdeaCandidateGeneratorConfig,
    build_deterministic_candidate_set_from_input_evidence,
)
from sis.strategy_idea_candidates.models import CandidateSetStatus
from sis.strategy_idea_candidates.service import write_strategy_idea_candidate_set
from sis.strategy_inputs.io import write_json_artifact
from sis.strategy_inputs.models import StrategyInputContract, StrategyInputContractValidation

from .fixtures import (
    valid_input_contract_payload,
    valid_input_validation_payload,
)


def _generator_config(*, candidate_cap: int = 3) -> StrategyIdeaCandidateGeneratorConfig:
    return StrategyIdeaCandidateGeneratorConfig(
        candidate_set_id="ndx-deterministic-candidates-001",
        candidate_cap=candidate_cap,
        shortlist_count=1,
        family_ids=[
            CandidateFamilyId.TREND_MOMENTUM,
            CandidateFamilyId.VOLATILITY_REGIME,
            CandidateFamilyId.LIQUIDITY_SPREAD,
            CandidateFamilyId.CROSS_SECTIONAL_RANK,
            CandidateFamilyId.MEAN_REVERSION,
        ],
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
        generated_at="2026-06-18T12:49:00Z",
    )


def _input_evidence(tmp_path) -> tuple[StrategyInputContract, StrategyInputContractValidation]:
    source = tmp_path / "data/research/ndx/source/ohlcv.csv"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text("ts,close,volume\n2026-06-17T21:00:00Z,1,100\n", encoding="utf-8")

    contract_payload = valid_input_contract_payload(sha256=sha256_file(source))
    validation_payload = valid_input_validation_payload()
    validation_payload["source_results"][0]["actual_sha256"] = sha256_file(source)
    validation_payload["source_results"][0]["declared_sha256"] = sha256_file(source)

    return (
        StrategyInputContract.model_validate(contract_payload),
        StrategyInputContractValidation.model_validate(validation_payload),
    )


def test_deterministic_generator_writes_same_candidate_set_json(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    contract, validation = _input_evidence(tmp_path)
    validation_path = tmp_path / "data/strategy_inputs/ndx/strategy_input_contract_validation.json"
    write_json_artifact(validation_path, valid_input_validation_payload())
    config = _generator_config(candidate_cap=3)

    first_set = build_deterministic_candidate_set_from_input_evidence(
        contract=contract,
        validation=validation,
        validation_path=validation_path,
        config=config,
    )
    second_set = build_deterministic_candidate_set_from_input_evidence(
        contract=contract,
        validation=validation,
        validation_path=validation_path,
        config=config,
    )

    assert first_set.model_dump(mode="json", exclude_none=True) == second_set.model_dump(
        mode="json", exclude_none=True
    )
    assert first_set.candidate_set_status is CandidateSetStatus.BUILT
    assert set(first_set.parameter_grids) == {
        "trend_momentum",
        "volatility_regime",
        "liquidity_spread",
        "cross_sectional_rank",
        "mean_reversion",
    }
    assert first_set.search_ledger_summary.candidate_cap == 3
    assert first_set.search_ledger_summary.cap_rejection_count > 0
    assert first_set.search_ledger_summary.duplicate_rejection_count == 0
    assert first_set.search_ledger_summary.parameter_grid_hash.startswith("sha256:")
    assert first_set.selection_policy.shortlisted_candidate_ids == [
        first_set.candidate_inventory[0].idea_candidate_id
    ]
    assert any(
        candidate.rejection_reason == "candidate cap exceeded before shortlist"
        for candidate in first_set.candidate_inventory
    )

    first_write = write_strategy_idea_candidate_set(
        candidate_set=first_set,
        out_dir=tmp_path / "data/strategy_idea_candidates/run-a",
    )
    second_write = write_strategy_idea_candidate_set(
        candidate_set=second_set,
        out_dir=tmp_path / "data/strategy_idea_candidates/run-b",
    )
    assert first_write.candidate_set_path.read_text(
        encoding="utf-8"
    ) == second_write.candidate_set_path.read_text(encoding="utf-8")
    payload = json.loads(first_write.candidate_set_path.read_text(encoding="utf-8"))
    assert "parameter_grids" in payload


def test_generator_records_duplicate_parameter_rejections(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    contract, validation = _input_evidence(tmp_path)
    validation_path = tmp_path / "data/strategy_inputs/ndx/strategy_input_contract_validation.json"
    write_json_artifact(validation_path, valid_input_validation_payload())
    config = _generator_config(candidate_cap=10).model_copy(
        update={
            "family_ids": [CandidateFamilyId.TREND_MOMENTUM],
            "parameter_grids": {
                "trend_momentum": [
                    {"lookback": 20, "threshold_z": 1.0},
                    {"lookback": 20, "threshold_z": 1.0},
                ]
            },
        }
    )

    candidate_set = build_deterministic_candidate_set_from_input_evidence(
        contract=contract,
        validation=validation,
        validation_path=validation_path,
        config=config,
    )

    assert candidate_set.search_ledger_summary.duplicate_rejection_count == 1
    assert any(
        candidate.rejection_reason == "duplicate parameterization: same family and parameter_set"
        for candidate in candidate_set.candidate_inventory
    )


def test_generator_blocks_non_pass_input_validation(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    contract, validation = _input_evidence(tmp_path)
    validation_payload = validation.model_dump(mode="json")
    validation_payload["validation_status"] = "NEEDS_FIX"
    validation = StrategyInputContractValidation.model_validate(validation_payload)
    validation_path = tmp_path / "data/strategy_inputs/ndx/strategy_input_contract_validation.json"
    write_json_artifact(validation_path, validation_payload)

    candidate_set = build_deterministic_candidate_set_from_input_evidence(
        contract=contract,
        validation=validation,
        validation_path=validation_path,
        config=_generator_config(candidate_cap=3),
    )

    assert candidate_set.candidate_set_status is CandidateSetStatus.BLOCKED_INPUT_EVIDENCE
    assert candidate_set.candidate_inventory == []


def test_generator_rejects_inconsistent_pass_source_evidence(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    contract, validation = _input_evidence(tmp_path)
    validation_payload = validation.model_dump(mode="json")
    validation_payload["source_results"][0]["status"] = "invalid"
    validation_payload["source_results"][0]["hash_matches"] = False
    validation = StrategyInputContractValidation.model_validate(validation_payload)
    validation_path = tmp_path / "data/strategy_inputs/ndx/strategy_input_contract_validation.json"
    write_json_artifact(validation_path, validation_payload)

    with pytest.raises(StrategyIdeaCandidateGeneratorError, match="invalid source evidence"):
        build_deterministic_candidate_set_from_input_evidence(
            contract=contract,
            validation=validation,
            validation_path=validation_path,
            config=_generator_config(candidate_cap=3),
        )
