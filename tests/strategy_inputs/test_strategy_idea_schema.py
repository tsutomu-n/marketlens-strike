from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator
import pytest
from pydantic import ValidationError

from sis.strategy_inputs.models import StrategyIdea


REPO_ROOT = Path(__file__).resolve().parents[2]


def _schema() -> dict:
    return json.loads(
        (REPO_ROOT / "schemas/strategy_idea.v1.schema.json").read_text(encoding="utf-8")
    )


def valid_idea_payload() -> dict:
    return {
        "schema_version": "strategy_idea.v1",
        "idea_id": "ndx-breakout-001",
        "created_at": "2026-06-18T12:45:00Z",
        "title": "NDX close breakout after volatility compression",
        "hypothesis": "NDX follow-through after low-volatility close breakout.",
        "mechanism": "trend_following",
        "timeframe": "1d",
        "instruments": ["NDX"],
        "required_input_contract_ids": ["ndx-breakout-inputs-001"],
        "baseline": {"name": "cash_or_no_trade", "expected_to_beat": True},
        "invalidation": ["no improvement over cash baseline"],
        "risk": {
            "max_position_notional_usd": 1000,
            "max_daily_loss_usd": 50,
            "kill_conditions": ["no fill in paper smoke"],
        },
        "execution_assumptions": {
            "order_type": "market_on_close_paper_intent",
            "slippage_model": "fixed_bps",
        },
        "authoring_intent": {
            "target": "strategy_authoring_draft",
            "auto_generate_spec": False,
        },
        "boundary": {
            "permits_live_order": False,
            "live_conversion_allowed": False,
            "wallet_used": False,
            "signing_used": False,
            "exchange_write_used": False,
        },
    }


def test_strategy_idea_schema_accepts_valid_payload() -> None:
    payload = valid_idea_payload()

    Draft202012Validator.check_schema(_schema())
    Draft202012Validator(_schema()).validate(payload)
    StrategyIdea.model_validate(payload)


@pytest.mark.parametrize(
    "field_name",
    ["hypothesis", "baseline", "invalidation", "risk", "required_input_contract_ids"],
)
def test_strategy_idea_requires_core_fields(field_name: str) -> None:
    payload = valid_idea_payload()
    payload.pop(field_name)

    assert list(Draft202012Validator(_schema()).iter_errors(payload))
    with pytest.raises(ValidationError):
        StrategyIdea.model_validate(payload)


def test_strategy_idea_rejects_auto_generate_and_permission() -> None:
    payload = valid_idea_payload()
    payload["authoring_intent"]["auto_generate_spec"] = True
    payload["boundary"]["exchange_write_used"] = True

    assert list(Draft202012Validator(_schema()).iter_errors(payload))
    with pytest.raises(ValidationError):
        StrategyIdea.model_validate(payload)
