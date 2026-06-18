from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from sis.strategy_micro_live_plan.models import MicroLiveMonitoringPlan
from sis.strategy_next_scale_plan.models import NextScaleRiskLimits
from sis.strategy_next_scale_plan.service import build_strategy_next_scale_plan


REPO_ROOT = Path(__file__).resolve().parents[2]


def _schema() -> dict:
    return json.loads(
        (REPO_ROOT / "schemas/strategy_next_scale_plan.v1.schema.json").read_text(encoding="utf-8")
    )


def _write_json(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return path


def _scale_decision(
    tmp_path: Path,
    *,
    status: str = "READY_FOR_HUMAN_SCALE_REVIEW",
    action: str = "PREPARE_NEXT_SCALE_PLAN",
) -> Path:
    return _write_json(
        tmp_path / "data/strategy_scale_decisions/ndx-breakout-001/decision.json",
        {
            "schema_version": "strategy_scale_decision.v1",
            "strategy_id": "ndx-breakout-001",
            "decision_id": "ndx-breakout-001-scale-decision",
            "created_at": "2026-06-19T04:00:00Z",
            "decision_status": status,
            "recommended_action": action,
            "next_scale_plan_allowed": False,
            "scale_up_execution_allowed": False,
            "live_allowed": False,
            "wallet_used": False,
            "signing_used": False,
            "exchange_write_used": False,
        },
    )


def _micro_live_plan(tmp_path: Path) -> Path:
    return _write_json(
        tmp_path / "data/strategy_micro_live_plans/ndx-breakout-001/plan.json",
        {
            "schema_version": "strategy_micro_live_plan.v1",
            "strategy_id": "ndx-breakout-001",
            "plan_id": "ndx-breakout-001-micro-live-plan",
            "risk_limits": {
                "max_order_notional_usd": 10,
                "max_position_notional_usd": 20,
                "max_daily_loss_usd": 3,
                "max_total_loss_usd": 6,
                "max_open_positions": 1,
                "allowed_symbols": ["NDX"],
                "session_window": "XNYS regular session",
            },
            "plan_status": "READY_FOR_HUMAN_MICRO_LIVE_REVIEW",
            "micro_live_execution_allowed": False,
            "paper_execution_allowed": False,
            "live_allowed": False,
        },
    )


def _risk_limits() -> NextScaleRiskLimits:
    return NextScaleRiskLimits(
        next_max_order_notional_usd=15,
        next_max_position_notional_usd=30,
        next_max_daily_loss_usd=4,
        next_max_total_loss_usd=8,
        next_max_open_positions=1,
        allowed_symbols=["NDX"],
        session_window="XNYS regular session",
    )


def _monitoring() -> MicroLiveMonitoringPlan:
    return MicroLiveMonitoringPlan(
        owner="operator",
        cadence="every 15 minutes while active",
        schedule_cancel_procedure="cancel all orders before session close",
        kill_switch_procedure="stop strategy and flatten through approved manual process",
    )


def test_next_scale_plan_builds_ready_schema_valid_artifact(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)

    result = build_strategy_next_scale_plan(
        strategy_id="ndx-breakout-001",
        scale_decision_path=_scale_decision(tmp_path),
        micro_live_plan_path=_micro_live_plan(tmp_path),
        out_dir=tmp_path / "data/strategy_next_scale_plans",
        risk_limits=_risk_limits(),
        monitoring_plan=_monitoring(),
    )

    assert result.plan.plan_status == "READY_FOR_HUMAN_NEXT_SCALE_REVIEW"
    assert result.plan.next_scale_execution_allowed is False
    assert result.plan.live_allowed is False
    payload = json.loads(result.plan_path.read_text(encoding="utf-8"))
    Draft202012Validator(_schema()).validate(payload)
    assert payload["next_scale_execution_allowed"] is False
    report = result.report_path.read_text(encoding="utf-8")
    assert "Strategy Next Scale Plan" in report
    assert "not next-scale execution permission" in report


def test_next_scale_plan_blocks_when_scale_decision_not_ready(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)

    result = build_strategy_next_scale_plan(
        strategy_id="ndx-breakout-001",
        scale_decision_path=_scale_decision(tmp_path, status="NEEDS_REPAIR"),
        micro_live_plan_path=_micro_live_plan(tmp_path),
        out_dir=tmp_path / "data/strategy_next_scale_plans",
        risk_limits=_risk_limits(),
        monitoring_plan=_monitoring(),
    )

    assert result.plan.plan_status == "NEEDS_SCALE_DECISION"
    assert "scale_decision_ready" in {
        condition.condition_id for condition in result.plan.failed_conditions
    }


def test_next_scale_plan_blocks_runaway_multiplier(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    limits = _risk_limits().model_copy(update={"next_max_order_notional_usd": 99})

    result = build_strategy_next_scale_plan(
        strategy_id="ndx-breakout-001",
        scale_decision_path=_scale_decision(tmp_path),
        micro_live_plan_path=_micro_live_plan(tmp_path),
        out_dir=tmp_path / "data/strategy_next_scale_plans",
        risk_limits=limits,
        monitoring_plan=_monitoring(),
    )

    assert result.plan.plan_status == "NEEDS_RISK_REPAIR"
    assert "max_order_notional_multiplier" in {
        condition.condition_id for condition in result.plan.failed_conditions
    }
