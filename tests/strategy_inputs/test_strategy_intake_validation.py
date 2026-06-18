from __future__ import annotations

from pathlib import Path

import yaml

from sis.backtest.artifact_io import sha256_file
from sis.strategy_inputs.models import IdeaIntakeDecision
from sis.strategy_inputs.validation import (
    validate_strategy_input_contract,
    validate_strategy_intake,
)
from .test_strategy_idea_schema import valid_idea_payload
from .test_strategy_input_contract_schema import valid_contract_payload


def _write_yaml(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return path


def _ready_contract_validation(tmp_path: Path) -> Path:
    source = tmp_path / "data/research/ndx/source/ohlcv.csv"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text("date,close\n2026-06-18,1\n", encoding="utf-8")
    contract = valid_contract_payload(sha256=sha256_file(source))
    contract_path = _write_yaml(tmp_path / "configs/strategy_inputs/input.yaml", contract)
    result = validate_strategy_input_contract(
        contract_path=contract_path,
        out_dir=tmp_path / "data/strategy_inputs/ndx-breakout-inputs-001",
    )
    return result.validation_path


def test_validate_strategy_intake_ready_for_authoring(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    validation_path = _ready_contract_validation(tmp_path)
    idea_path = _write_yaml(tmp_path / "configs/strategy_ideas/idea.yaml", valid_idea_payload())

    result = validate_strategy_intake(
        idea_path=idea_path,
        input_contract_validation_paths=[validation_path],
        out_dir=tmp_path / "data/strategy_ideas/ndx-breakout-001",
    )

    assert result.decision.decision is IdeaIntakeDecision.READY_FOR_AUTHORING_DRAFT
    assert result.decision.required_actions == []
    assert result.decision_path.exists()
    assert result.report_path.exists()


def test_validate_strategy_intake_missing_contract_needs_data_check(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    idea_path = _write_yaml(tmp_path / "configs/strategy_ideas/idea.yaml", valid_idea_payload())

    result = validate_strategy_intake(
        idea_path=idea_path,
        input_contract_validation_paths=[],
        out_dir=tmp_path / "data/strategy_ideas/ndx-breakout-001",
    )

    assert result.decision.decision is IdeaIntakeDecision.NEEDS_DATA_CHECK
    assert result.decision.summary.missing_required_inputs is True


def test_validate_strategy_intake_missing_required_inputs_needs_data_check(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    payload = valid_idea_payload()
    payload.pop("required_input_contract_ids")
    idea_path = _write_yaml(tmp_path / "configs/strategy_ideas/idea.yaml", payload)

    result = validate_strategy_intake(
        idea_path=idea_path,
        input_contract_validation_paths=[],
        out_dir=tmp_path / "data/strategy_ideas/ndx-breakout-001",
    )

    assert result.decision.decision is IdeaIntakeDecision.NEEDS_DATA_CHECK
    assert result.decision.summary.missing_required_inputs is True
    assert result.decision_path.exists()
    assert result.report_path.exists()


def test_validate_strategy_intake_missing_risk_needs_risk_spec(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    payload = valid_idea_payload()
    payload.pop("risk")
    idea_path = _write_yaml(tmp_path / "configs/strategy_ideas/idea.yaml", payload)

    result = validate_strategy_intake(
        idea_path=idea_path,
        input_contract_validation_paths=[],
        out_dir=tmp_path / "data/strategy_ideas/ndx-breakout-001",
    )

    assert result.decision.decision is IdeaIntakeDecision.NEEDS_RISK_SPEC
    assert result.decision.summary.missing_risk is True
    assert result.decision_path.exists()
    assert result.report_path.exists()


def test_validate_strategy_intake_missing_baseline_needs_spec(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    payload = valid_idea_payload()
    payload.pop("baseline")
    idea_path = _write_yaml(tmp_path / "configs/strategy_ideas/idea.yaml", payload)

    result = validate_strategy_intake(
        idea_path=idea_path,
        input_contract_validation_paths=[],
        out_dir=tmp_path / "data/strategy_ideas/ndx-breakout-001",
    )

    assert result.decision.decision is IdeaIntakeDecision.NEEDS_SPEC
    assert result.decision.summary.missing_baseline is True
    assert result.decision_path.exists()
    assert result.report_path.exists()
