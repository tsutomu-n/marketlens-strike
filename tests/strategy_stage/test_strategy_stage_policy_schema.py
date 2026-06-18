from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator
import pytest
from pydantic import ValidationError

from sis.strategy_stage.models import StageName, StrategyStagePolicy


REPO_ROOT = Path(__file__).resolve().parents[2]


def _schema() -> dict:
    return json.loads(
        (REPO_ROOT / "schemas/strategy_stage_policy.v1.schema.json").read_text(encoding="utf-8")
    )


def valid_stage_policy_payload() -> dict:
    return {
        "schema_version": "strategy_stage_policy.v1",
        "policy_id": "personal_default_v1",
        "description": "Personal default stage policy.",
        "fixed_safety": {
            "require_source_hashes": True,
            "require_schema_versions": True,
            "forbid_live_order_before_micro_live_gate": True,
            "forbid_wallet_before_micro_live_gate": True,
            "forbid_signing_before_micro_live_gate": True,
            "forbid_exchange_write_before_micro_live_gate": True,
            "require_manual_override_reason": True,
        },
        "stages": {
            "paper_smoke": {
                "min_fills": 3,
                "min_trading_days": 1,
                "max_order_notional_usd": 100,
                "max_position_notional_usd": 300,
                "max_orders_per_day": 10,
                "stop_after_consecutive_errors": 2,
            },
            "normal_paper_observation": {
                "min_fills": 20,
                "min_trading_days": 10,
                "max_no_fill_rate": 0.4,
                "max_slippage_bps": 20,
                "max_drawdown_vs_backtest_ratio": 2.0,
                "max_blocked_rate": 0.5,
                "max_consecutive_blocked": 3,
            },
            "drift_review": {
                "min_fills": 20,
                "min_trading_days": 10,
            },
            "micro_live_plan": {
                "max_order_notional_usd": 50,
                "max_total_notional_usd": 100,
                "max_daily_loss_usd": 20,
                "max_total_loss_usd": 50,
                "max_runtime_days": 3,
                "require_manual_start": True,
                "require_kill_switch": True,
                "require_monitoring_plan": True,
            },
        },
        "strategy_profiles": {
            "intraday_momentum": {"paper_smoke": {"min_fills": 10, "min_trading_days": 1}}
        },
        "boundary": {
            "permits_live_order": False,
            "live_conversion_allowed": False,
            "wallet_used": False,
            "signing_used": False,
            "exchange_write_used": False,
        },
    }


def test_strategy_stage_policy_schema_accepts_valid_payload() -> None:
    payload = valid_stage_policy_payload()

    Draft202012Validator.check_schema(_schema())
    Draft202012Validator(_schema()).validate(payload)
    StrategyStagePolicy.model_validate(payload)


def test_strategy_stage_policy_rejects_disabled_fixed_safety() -> None:
    payload = valid_stage_policy_payload()
    payload["fixed_safety"]["forbid_wallet_before_micro_live_gate"] = False

    assert list(Draft202012Validator(_schema()).iter_errors(payload))
    with pytest.raises(ValidationError):
        StrategyStagePolicy.model_validate(payload)


def test_stage_name_enum_matches_schema() -> None:
    enum_values = set(_schema()["properties"]["stages"]["properties"].keys())

    assert enum_values == {value.value for value in StageName}


def test_strategy_stage_policy_requires_every_stage() -> None:
    payload = valid_stage_policy_payload()
    del payload["stages"]["drift_review"]

    errors = list(Draft202012Validator(_schema()).iter_errors(payload))
    assert errors
    with pytest.raises(ValidationError, match="stages missing required"):
        StrategyStagePolicy.model_validate(payload)


def test_strategy_stage_policy_rejects_rate_over_one() -> None:
    payload = valid_stage_policy_payload()
    payload["stages"]["normal_paper_observation"]["max_no_fill_rate"] = 1.2

    errors = list(Draft202012Validator(_schema()).iter_errors(payload))
    assert errors
    with pytest.raises(ValidationError):
        StrategyStagePolicy.model_validate(payload)
