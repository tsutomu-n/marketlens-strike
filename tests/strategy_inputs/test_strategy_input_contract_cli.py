from __future__ import annotations

from pathlib import Path

import yaml
from typer.testing import CliRunner

from sis.backtest.artifact_io import sha256_file
from sis.cli import app
from support.cli import normalized_stdout
from .test_strategy_input_contract_schema import valid_contract_payload


runner = CliRunner()


def _write_contract(tmp_path: Path, *, valid_source: bool) -> Path:
    source = tmp_path / "data/research/ndx/source/ohlcv.csv"
    sha256 = "sha256:" + "a" * 64
    if valid_source:
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text("date,close\n2026-06-18,1\n", encoding="utf-8")
        sha256 = sha256_file(source)
    payload = valid_contract_payload(sha256=sha256)
    path = tmp_path / "configs/strategy_inputs/input.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return path


def test_strategy_input_contract_validate_help() -> None:
    result = runner.invoke(app, ["strategy-input-contract-validate", "--help"])
    stdout = normalized_stdout(result)

    assert result.exit_code == 0
    assert "--contract" in stdout
    assert "--strict" in stdout


def test_strategy_input_contract_validate_cli_success(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    contract_path = _write_contract(tmp_path, valid_source=True)

    result = runner.invoke(
        app,
        [
            "strategy-input-contract-validate",
            "--contract",
            str(contract_path),
            "--out",
            str(tmp_path / "data/strategy_inputs/ndx-breakout-inputs-001"),
        ],
    )

    assert result.exit_code == 0
    assert "validation_status=PASS" in result.stdout
    assert (tmp_path / "data/strategy_inputs/ndx-breakout-inputs-001").exists()


def test_strategy_input_contract_validate_cli_strict_needs_fix_exits_two(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    contract_path = _write_contract(tmp_path, valid_source=False)

    result = runner.invoke(
        app,
        [
            "strategy-input-contract-validate",
            "--contract",
            str(contract_path),
            "--out",
            str(tmp_path / "data/strategy_inputs/ndx-breakout-inputs-001"),
            "--strict",
        ],
    )

    assert result.exit_code == 2
    assert "validation_status=NEEDS_FIX" in result.stdout
