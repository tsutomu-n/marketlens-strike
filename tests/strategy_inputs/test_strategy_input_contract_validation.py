from __future__ import annotations

from pathlib import Path

from sis.backtest.artifact_io import sha256_file
from sis.strategy_inputs.models import InputValidationStatus
from sis.strategy_inputs.validation import validate_strategy_input_contract
from .test_strategy_input_contract_schema import valid_contract_payload

import yaml


def _write_contract(tmp_path: Path, payload: dict) -> Path:
    path = tmp_path / "configs/strategy_inputs/input.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return path


def test_validate_strategy_input_contract_passes(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    source = tmp_path / "data/research/ndx/source/ohlcv.csv"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text("date,close\n2026-06-18,1\n", encoding="utf-8")
    payload = valid_contract_payload(sha256=sha256_file(source))
    contract_path = _write_contract(tmp_path, payload)

    result = validate_strategy_input_contract(
        contract_path=contract_path,
        out_dir=tmp_path / "data/strategy_inputs/ndx-breakout-inputs-001",
        validated_at="2026-06-18T12:45:00Z",
    )

    assert result.validation.validation_status is InputValidationStatus.PASS
    assert result.validation.summary.missing_required_count == 0
    assert result.validation.source_results[0].hash_matches is True
    assert result.validation_path.exists()
    assert result.report_path.exists()


def test_validate_strategy_input_contract_checks_columns_and_timestamps(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    source = tmp_path / "data/research/ndx/source/ohlcv.csv"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text(
        "ts,available_at,close\n2026-06-18T12:00:00Z,2026-06-18T12:01:00Z,1\n",
        encoding="utf-8",
    )
    payload = valid_contract_payload(sha256=sha256_file(source))
    payload["sources"][0]["validation_expectations"] = {
        "required_columns": ["close"],
        "timestamp_column": "ts",
        "max_allowed_timestamp": "2026-06-18T12:00:00Z",
        "available_at_column": "available_at",
        "available_at_column_required": True,
    }
    contract_path = _write_contract(tmp_path, payload)

    result = validate_strategy_input_contract(
        contract_path=contract_path,
        out_dir=tmp_path / "data/strategy_inputs/ndx-breakout-inputs-001",
    )

    source_result = result.validation.source_results[0]
    assert result.validation.validation_status is InputValidationStatus.PASS
    assert source_result.required_columns_present is True
    assert source_result.available_at_column_present is True
    assert source_result.timestamp_check_passed is True
    assert source_result.max_observed_timestamp == "2026-06-18T12:00:00Z"


def test_validate_strategy_input_contract_missing_required_column_needs_fix(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    source = tmp_path / "data/research/ndx/source/ohlcv.csv"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text("ts,close\n2026-06-18T12:00:00Z,1\n", encoding="utf-8")
    payload = valid_contract_payload(sha256=sha256_file(source))
    payload["sources"][0]["validation_expectations"] = {
        "required_columns": ["close", "spread_bps"],
        "available_at_column": "available_at",
        "available_at_column_required": True,
    }
    contract_path = _write_contract(tmp_path, payload)

    result = validate_strategy_input_contract(
        contract_path=contract_path,
        out_dir=tmp_path / "data/strategy_inputs/ndx-breakout-inputs-001",
    )

    source_result = result.validation.source_results[0]
    assert result.validation.validation_status is InputValidationStatus.NEEDS_FIX
    assert result.validation.summary.invalid_required_count == 1
    assert result.validation.summary.column_check_failure_count == 1
    assert source_result.missing_columns == ["available_at", "spread_bps"]
    assert "MISSING_REQUIRED_COLUMN" in (source_result.error or "")
    assert "AVAILABLE_AT_COLUMN_MISSING" in (source_result.error or "")


def test_validate_strategy_input_contract_future_timestamp_needs_fix(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    source = tmp_path / "data/research/ndx/source/ohlcv.csv"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text("ts,close\n2026-06-19T12:00:00Z,1\n", encoding="utf-8")
    payload = valid_contract_payload(sha256=sha256_file(source))
    payload["sources"][0]["validation_expectations"] = {
        "required_columns": ["close"],
        "timestamp_column": "ts",
        "max_allowed_timestamp": "2026-06-18T12:00:00Z",
    }
    contract_path = _write_contract(tmp_path, payload)

    result = validate_strategy_input_contract(
        contract_path=contract_path,
        out_dir=tmp_path / "data/strategy_inputs/ndx-breakout-inputs-001",
    )

    source_result = result.validation.source_results[0]
    assert result.validation.validation_status is InputValidationStatus.NEEDS_FIX
    assert result.validation.summary.invalid_required_count == 1
    assert result.validation.summary.timestamp_violation_count == 1
    assert source_result.timestamp_check_passed is False
    assert "timestamp exceeds" in (source_result.error or "")


def test_validate_strategy_input_contract_missing_required_needs_fix(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    contract_path = _write_contract(tmp_path, valid_contract_payload())

    result = validate_strategy_input_contract(
        contract_path=contract_path,
        out_dir=tmp_path / "data/strategy_inputs/ndx-breakout-inputs-001",
    )

    assert result.validation.validation_status is InputValidationStatus.NEEDS_FIX
    assert result.validation.summary.missing_required_count == 1


def test_validate_strategy_input_contract_hash_mismatch_needs_fix(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    source = tmp_path / "data/research/ndx/source/ohlcv.csv"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text("changed\n", encoding="utf-8")
    contract_path = _write_contract(tmp_path, valid_contract_payload())

    result = validate_strategy_input_contract(
        contract_path=contract_path,
        out_dir=tmp_path / "data/strategy_inputs/ndx-breakout-inputs-001",
    )

    assert result.validation.validation_status is InputValidationStatus.NEEDS_FIX
    assert result.validation.summary.invalid_required_count == 1
    assert result.validation.source_results[0].hash_matches is False


def test_validate_strategy_input_contract_boundary_violation_blocks(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    payload = valid_contract_payload()
    payload["boundary"]["wallet_used"] = True
    contract_path = _write_contract(tmp_path, payload)

    result = validate_strategy_input_contract(
        contract_path=contract_path,
        out_dir=tmp_path / "data/strategy_inputs/ndx-breakout-inputs-001",
    )

    assert result.validation.validation_status is InputValidationStatus.BLOCKED_BOUNDARY_VIOLATION
    assert result.validation.summary.boundary_violation_count == 1
