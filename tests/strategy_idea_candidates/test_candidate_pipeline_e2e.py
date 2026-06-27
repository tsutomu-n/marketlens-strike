from __future__ import annotations

import json

from jsonschema import Draft202012Validator

from sis.backtest.artifact_io import sha256_file
from sis.strategy_idea_candidates.generator import (
    CandidateFamilyId,
    StrategyIdeaCandidateGeneratorConfig,
    build_deterministic_candidate_set_from_input_evidence,
)
from sis.strategy_idea_candidates.models import StrategyIdeaCandidateSet
from sis.strategy_idea_candidates.operator_review import (
    write_strategy_idea_candidate_operator_review,
)
from sis.strategy_idea_candidates.policies import validate_split_and_leakage_policy
from sis.strategy_idea_candidates.service import write_strategy_idea_candidate_set
from sis.strategy_idea_candidates.export import export_shortlisted_strategy_ideas
from sis.strategy_inputs.io import write_json_artifact
from sis.strategy_inputs.models import StrategyInputContract, StrategyInputContractValidation
from sis.strategy_inputs.validation import validate_strategy_intake

from .fixtures import valid_input_contract_payload, valid_input_validation_payload
from .test_candidate_export import _schema


def test_candidate_generation_fixture_e2e_to_intake_validation(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    source = tmp_path / "data/research/ndx/source/ohlcv.csv"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text("ts,close,volume\n2026-06-17T21:00:00Z,1,100\n", encoding="utf-8")
    source_hash = sha256_file(source)

    contract = StrategyInputContract.model_validate(valid_input_contract_payload(sha256=source_hash))
    validation_payload = valid_input_validation_payload()
    validation_payload["source_results"][0]["actual_sha256"] = source_hash
    validation_payload["source_results"][0]["declared_sha256"] = source_hash
    validation = StrategyInputContractValidation.model_validate(validation_payload)
    validation_path = tmp_path / "data/strategy_inputs/ndx/strategy_input_contract_validation.json"
    write_json_artifact(validation_path, validation_payload)

    candidate_set = build_deterministic_candidate_set_from_input_evidence(
        contract=contract,
        validation=validation,
        validation_path=validation_path,
        config=StrategyIdeaCandidateGeneratorConfig(
            candidate_set_id="ndx-pipeline-e2e-001",
            family_ids=[
                CandidateFamilyId.TREND_MOMENTUM,
                CandidateFamilyId.MEAN_REVERSION,
            ],
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
            generated_at="2026-06-18T12:51:00Z",
        ),
    )
    StrategyIdeaCandidateSet.model_validate(candidate_set.model_dump(mode="json"))
    policy_validation = validate_split_and_leakage_policy(candidate_set)
    assert policy_validation.passed is True

    write_result = write_strategy_idea_candidate_set(
        candidate_set=candidate_set,
        out_dir=tmp_path / "data/strategy_idea_candidates/e2e",
    )
    review_result = write_strategy_idea_candidate_operator_review(
        candidate_set=candidate_set,
        policy_validation=policy_validation,
        out_dir=tmp_path / "data/strategy_idea_candidates/e2e/review",
    )
    export_result = export_shortlisted_strategy_ideas(
        candidate_set=candidate_set,
        candidate_set_path=write_result.candidate_set_path,
        out_dir=tmp_path / "data/strategy_idea_candidates/e2e/exported_strategy_ideas",
        created_at="2026-06-18T12:52:00Z",
    )

    manifest_payload = json.loads(export_result.manifest_path.read_text(encoding="utf-8"))
    Draft202012Validator(
        _schema("strategy_idea_candidate_export_manifest.v1.schema.json")
    ).validate(manifest_payload)
    idea_payload = json.loads(export_result.idea_paths[0].read_text(encoding="utf-8"))
    Draft202012Validator(_schema("strategy_idea.v1.schema.json")).validate(idea_payload)
    assert "candidate_set_path" not in idea_payload

    intake = validate_strategy_intake(
        idea_path=export_result.idea_paths[0],
        input_contract_validation_paths=[validation_path],
        out_dir=tmp_path / "data/strategy_idea_candidates/e2e/intake",
        decided_at="2026-06-18T12:53:00Z",
    )

    assert intake.decision.decision.value == "READY_FOR_AUTHORING_DRAFT"
    assert write_result.candidate_set_path.exists()
    assert write_result.report_path.exists()
    assert review_result.report_path.exists()
    assert export_result.manifest_path.exists()
