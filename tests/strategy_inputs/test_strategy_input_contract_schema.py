from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator
import pytest
from pydantic import ValidationError

from sis.strategy_inputs.models import InputSourceType, StrategyInputContract


REPO_ROOT = Path(__file__).resolve().parents[2]


def _schema() -> dict:
    return json.loads(
        (REPO_ROOT / "schemas/strategy_input_contract.v1.schema.json").read_text(encoding="utf-8")
    )


def valid_contract_payload(sha256: str | None = None) -> dict:
    return {
        "schema_version": "strategy_input_contract.v1",
        "contract_id": "ndx-breakout-inputs-001",
        "created_at": "2026-06-18T12:45:00Z",
        "producer": {"tool": "sis", "command": "manual"},
        "strategy_scope": {
            "strategy_family": "breakout",
            "instruments": ["NDX"],
            "timeframe": "1d",
            "intended_use": "research_backtest_only",
        },
        "sources": [
            {
                "source_id": "ndx_ohlcv_daily",
                "source_type": "raw_market_data",
                "path": "data/research/ndx/source/ohlcv.csv",
                "required": True,
                "declared_sha256": sha256 or "sha256:" + "a" * 64,
                "schema_version": "market_ohlcv.v1",
                "generated_at": "2026-06-18T00:00:00Z",
                "available_at": "2026-06-18T00:05:00Z",
                "revision_policy": "append_only",
                "survivorship_policy": "current_constituents_not_allowed",
                "execution_reality": {
                    "includes_fills": False,
                    "includes_slippage": False,
                    "includes_latency": False,
                    "assumed_order_type": "paper_only_intent",
                },
            }
        ],
        "known_gaps": ["no intraday spread data"],
        "boundary": {
            "permits_live_order": False,
            "live_conversion_allowed": False,
            "wallet_used": False,
            "signing_used": False,
            "exchange_write_used": False,
        },
    }


def test_strategy_input_contract_schema_accepts_valid_payload(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    payload = valid_contract_payload()

    Draft202012Validator.check_schema(_schema())
    Draft202012Validator(_schema()).validate(payload)
    StrategyInputContract.model_validate(payload)


def test_strategy_input_contract_pydantic_dump_matches_tracked_schema(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    contract = StrategyInputContract.model_validate(valid_contract_payload())
    payload = contract.model_dump(mode="json", exclude_none=True)

    Draft202012Validator(_schema()).validate(payload)


def test_strategy_input_contract_schema_accepts_validation_expectations(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    payload = valid_contract_payload()
    payload["sources"][0]["validation_expectations"] = {
        "required_columns": ["ts", "close", "available_at"],
        "timestamp_column": "ts",
        "max_allowed_timestamp": "2026-06-18T12:00:00Z",
        "available_at_column": "available_at",
        "available_at_column_required": True,
    }

    Draft202012Validator(_schema()).validate(payload)
    contract = StrategyInputContract.model_validate(payload)
    dumped = contract.model_dump(mode="json", exclude_none=True)
    Draft202012Validator(_schema()).validate(dumped)


@pytest.mark.parametrize(
    ("path", "sha256", "permission_true", "extra"),
    [
        ("/abs/file.csv", "sha256:" + "a" * 64, False, False),
        ("data/secrets/file.csv", "sha256:" + "a" * 64, False, False),
        ("data/file.csv", "a" * 64, False, False),
        ("data/file.csv", "sha256:" + "a" * 64, True, False),
        ("data/file.csv", "sha256:" + "a" * 64, False, True),
    ],
)
def test_strategy_input_contract_rejects_unsafe_shape(
    tmp_path, monkeypatch, path: str, sha256: str, permission_true: bool, extra: bool
) -> None:
    monkeypatch.chdir(tmp_path)
    payload = valid_contract_payload(sha256=sha256)
    payload["sources"][0]["path"] = path
    if permission_true:
        payload["boundary"]["wallet_used"] = True
    if extra:
        payload["extra"] = "nope"

    assert list(Draft202012Validator(_schema()).iter_errors(payload))
    with pytest.raises(ValidationError):
        StrategyInputContract.model_validate(payload)


def test_strategy_input_source_type_enum_matches_schema() -> None:
    enum_values = set(
        _schema()["properties"]["sources"]["items"]["properties"]["source_type"]["enum"]
    )

    assert enum_values == {value.value for value in InputSourceType}
