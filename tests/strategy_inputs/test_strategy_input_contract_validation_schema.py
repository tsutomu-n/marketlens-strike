from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator
import pytest
from pydantic import ValidationError

from sis.strategy_inputs.models import InputValidationStatus, StrategyInputContractValidation


REPO_ROOT = Path(__file__).resolve().parents[2]


def _schema() -> dict:
    return json.loads(
        (REPO_ROOT / "schemas/strategy_input_contract_validation.v1.schema.json").read_text(
            encoding="utf-8"
        )
    )


def valid_validation_payload() -> dict:
    return {
        "schema_version": "strategy_input_contract_validation.v1",
        "contract_id": "ndx-breakout-inputs-001",
        "validated_at": "2026-06-18T12:45:00Z",
        "producer": {"tool": "sis", "command": "strategy-input-contract-validate"},
        "validation_status": "PASS",
        "strict": False,
        "source_results": [
            {
                "source_id": "ndx_ohlcv_daily",
                "status": "present",
                "path": "data/research/ndx/source/ohlcv.csv",
                "actual_sha256": "sha256:" + "a" * 64,
                "declared_sha256": "sha256:" + "a" * 64,
                "hash_matches": True,
                "available_at_present": True,
                "generated_before_available": True,
            }
        ],
        "summary": {
            "missing_required_count": 0,
            "invalid_required_count": 0,
            "boundary_violation_count": 0,
            "warning_count": 0,
            "column_check_failure_count": 0,
            "timestamp_violation_count": 0,
        },
        "boundary": {
            "permits_live_order": False,
            "live_conversion_allowed": False,
            "wallet_used": False,
            "signing_used": False,
            "exchange_write_used": False,
        },
    }


def test_input_contract_validation_schema_accepts_valid_payload(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    payload = valid_validation_payload()

    Draft202012Validator.check_schema(_schema())
    Draft202012Validator(_schema()).validate(payload)
    StrategyInputContractValidation.model_validate(payload)


def test_input_contract_validation_schema_rejects_permission_true() -> None:
    payload = valid_validation_payload()
    payload["boundary"]["wallet_used"] = True

    assert list(Draft202012Validator(_schema()).iter_errors(payload))
    with pytest.raises(ValidationError):
        StrategyInputContractValidation.model_validate(payload)


def test_input_validation_status_enum_matches_schema() -> None:
    enum_values = set(_schema()["properties"]["validation_status"]["enum"])

    assert enum_values == {status.value for status in InputValidationStatus}
