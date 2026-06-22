from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator
import pytest
from pydantic import ValidationError

from sis.strategy_case_index.models import StrategyCaseIndex


REPO_ROOT = Path(__file__).resolve().parents[2]


def _schema() -> dict:
    return json.loads(
        (REPO_ROOT / "schemas/strategy_case_index.v1.schema.json").read_text(encoding="utf-8")
    )


def _index_payload() -> dict:
    return {
        "schema_version": "strategy_case_index.v1",
        "index_id": "case-index-001",
        "created_at": "2026-06-22T09:00:00Z",
        "producer": {"tool": "sis", "command": "strategy-case-index-build"},
        "case_count": 1,
        "strategy_count": 1,
        "cases": [
            {
                "case_id": "case-001",
                "strategy_id": "ndx-breakout-001",
                "case_path": "data/strategy_cases/ndx-breakout-001/strategy_case_lite.json",
                "case_sha256": "sha256:" + "a" * 64,
                "latest_status": "READY_FOR_HUMAN_REVIEW",
                "artifact_count": 2,
                "timeline_count": 2,
                "open_actions": ["REVISE_STRATEGY"],
                "blocked_reasons": ["runtime_no_fill_rate_within_limit"],
                "updated_at": "2026-06-22T08:55:00Z",
            }
        ],
        "strategies": [
            {
                "strategy_id": "ndx-breakout-001",
                "case_count": 1,
                "latest_case_id": "case-001",
                "latest_case_path": "data/strategy_cases/ndx-breakout-001/strategy_case_lite.json",
                "latest_status": "READY_FOR_HUMAN_REVIEW",
                "open_actions": ["REVISE_STRATEGY"],
                "blocked_reasons": ["runtime_no_fill_rate_within_limit"],
            }
        ],
        "source_artifacts": [
            {
                "path": "data/strategy_cases/ndx-breakout-001/strategy_case_lite.json",
                "sha256": "sha256:" + "a" * 64,
                "schema_version": "strategy_case_lite.v1",
            }
        ],
        "paper_execution_allowed": False,
        "live_allowed": False,
        "boundary": {
            "permits_live_order": False,
            "live_conversion_allowed": False,
            "wallet_used": False,
            "signing_used": False,
            "exchange_write_used": False,
        },
        "index_boundary": {
            "permits_live_order": False,
            "live_conversion_allowed": False,
            "wallet_used": False,
            "signing_used": False,
            "exchange_write_used": False,
            "paper_execution_allowed": False,
            "live_allowed": False,
            "db_persistence_allowed": False,
        },
    }


def test_strategy_case_index_schema_accepts_valid_payload() -> None:
    payload = _index_payload()

    Draft202012Validator.check_schema(_schema())
    Draft202012Validator(_schema()).validate(payload)
    model = StrategyCaseIndex.model_validate(payload)
    dumped = model.model_dump(mode="json", exclude_none=True)
    Draft202012Validator(_schema()).validate(dumped)


@pytest.mark.parametrize(
    ("field_path", "value"),
    [
        (("schema_version",), "strategy_case_index.v2"),
        (("case_count",), 2),
        (("strategy_count",), 2),
        (("boundary", "wallet_used"), True),
        (("index_boundary", "db_persistence_allowed"), True),
        (("cases", 0, "case_path"), "/abs/case.json"),
    ],
)
def test_strategy_case_index_rejects_unsafe_or_inconsistent_shape(
    field_path: tuple, value: object
) -> None:
    payload = _index_payload()
    target = payload
    for key in field_path[:-1]:
        target = target[key]
    target[field_path[-1]] = value

    schema_errors = list(Draft202012Validator(_schema()).iter_errors(payload))
    if field_path in {("case_count",), ("strategy_count",)}:
        assert not schema_errors
    else:
        assert schema_errors
    with pytest.raises(ValidationError):
        StrategyCaseIndex.model_validate(payload)
