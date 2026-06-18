from __future__ import annotations

from pathlib import Path

import yaml
from typer.testing import CliRunner

from sis.backtest.artifact_io import sha256_file
from sis.cli import app
from support.cli import normalized_stdout
from sis.strategy_inputs.validation import validate_strategy_input_contract
from .test_strategy_idea_schema import valid_idea_payload
from .test_strategy_input_contract_schema import valid_contract_payload


runner = CliRunner()


def _write_ready_inputs(tmp_path: Path) -> tuple[Path, Path]:
    source = tmp_path / "data/research/ndx/source/ohlcv.csv"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text("date,close\n2026-06-18,1\n", encoding="utf-8")
    contract = valid_contract_payload(sha256=sha256_file(source))
    contract_path = tmp_path / "configs/strategy_inputs/input.yaml"
    contract_path.parent.mkdir(parents=True, exist_ok=True)
    contract_path.write_text(yaml.safe_dump(contract, sort_keys=False), encoding="utf-8")
    validation = validate_strategy_input_contract(
        contract_path=contract_path,
        out_dir=tmp_path / "data/strategy_inputs/ndx-breakout-inputs-001",
    )
    idea_path = tmp_path / "configs/strategy_ideas/idea.yaml"
    idea_path.parent.mkdir(parents=True, exist_ok=True)
    idea_path.write_text(yaml.safe_dump(valid_idea_payload(), sort_keys=False), encoding="utf-8")
    return idea_path, validation.validation_path


def test_strategy_intake_validate_help() -> None:
    result = runner.invoke(app, ["strategy-intake-validate", "--help"])
    stdout = normalized_stdout(result)

    assert result.exit_code == 0
    assert "--idea" in stdout
    assert "Input contract" in stdout


def test_strategy_intake_validate_cli_success(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    idea_path, validation_path = _write_ready_inputs(tmp_path)

    result = runner.invoke(
        app,
        [
            "strategy-intake-validate",
            "--idea",
            str(idea_path),
            "--input-contract-validation",
            str(validation_path),
            "--out",
            str(tmp_path / "data/strategy_ideas/ndx-breakout-001"),
        ],
    )

    assert result.exit_code == 0
    assert "decision=READY_FOR_AUTHORING_DRAFT" in result.stdout
