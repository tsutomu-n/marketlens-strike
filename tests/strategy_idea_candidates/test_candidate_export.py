from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from sis.backtest.artifact_io import sha256_file
from sis.strategy_idea_candidates.export import export_shortlisted_strategy_ideas
from sis.strategy_idea_candidates.models import StrategyIdeaCandidateSet
from sis.strategy_idea_candidates.service import write_strategy_idea_candidate_set
from sis.strategy_inputs.io import write_json_artifact
from sis.strategy_inputs.models import StrategyIdea
from sis.strategy_inputs.validation import validate_strategy_intake

from .fixtures import valid_candidate_set_payload, valid_input_validation_payload


REPO_ROOT = Path(__file__).resolve().parents[2]


def _schema(name: str) -> dict:
    return json.loads((REPO_ROOT / f"schemas/{name}").read_text(encoding="utf-8"))


def test_shortlist_export_writes_strategy_idea_and_sidecar_manifest(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    candidate_set = StrategyIdeaCandidateSet.model_validate(valid_candidate_set_payload())
    write_result = write_strategy_idea_candidate_set(
        candidate_set=candidate_set,
        out_dir=tmp_path / "data/strategy_idea_candidates/run-a",
    )
    validation_path = tmp_path / "data/strategy_inputs/ndx/strategy_input_contract_validation.json"
    write_json_artifact(validation_path, valid_input_validation_payload())

    export_result = export_shortlisted_strategy_ideas(
        candidate_set=candidate_set,
        candidate_set_path=write_result.candidate_set_path,
        out_dir=tmp_path / "data/strategy_idea_candidates/run-a/exported_strategy_ideas",
        created_at="2026-06-18T12:47:00Z",
    )

    manifest_payload = json.loads(export_result.manifest_path.read_text(encoding="utf-8"))
    Draft202012Validator(_schema("strategy_idea_candidate_export_manifest.v1.schema.json")).validate(
        manifest_payload
    )
    assert manifest_payload["candidate_set_path"] == (
        "data/strategy_idea_candidates/run-a/strategy_idea_candidate_set.json"
    )
    assert manifest_payload["candidate_set_sha256"] == sha256_file(
        write_result.candidate_set_path
    )

    idea_payload = json.loads(export_result.idea_paths[0].read_text(encoding="utf-8"))
    Draft202012Validator(_schema("strategy_idea.v1.schema.json")).validate(idea_payload)
    StrategyIdea.model_validate(idea_payload)
    assert "candidate_set_path" not in idea_payload
    assert "candidate_set_sha256" not in idea_payload

    intake = validate_strategy_intake(
        idea_path=export_result.idea_paths[0],
        input_contract_validation_paths=[validation_path],
        out_dir=tmp_path / "data/strategy_idea_candidates/run-a/intake",
        decided_at="2026-06-18T12:48:00Z",
    )

    assert intake.decision.decision.value == "READY_FOR_AUTHORING_DRAFT"
